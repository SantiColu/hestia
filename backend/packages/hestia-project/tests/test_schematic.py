import pytest

from hestia_project.catalog import StageType, TemplateId
from hestia_project.errors import InvalidOperationError, NotFoundError
from hestia_project.model import Cell, CellStatus, Link, Position, Project
from hestia_project.schematic import (
    Blueprint,
    add_cell,
    branch,
    branch_options,
    branch_targets,
    check_link,
    create_system,
    delete_cell,
    delete_system,
    duplicate_system,
    invalidate,
    link,
    link_targets,
    move_system,
    rename_cell,
    rename_system,
    unlink,
)

S = StageType
PHASE_0 = Blueprint(template=TemplateId.PHASE_0)
PHASE_1 = Blueprint(template=TemplateId.PHASE_1)


def cells_by_stage(project: Project, system_name: str) -> dict[StageType, Cell]:
    system = next(s for s in project.systems if s.name == system_name)
    cells = [c for c in project.cells if c.id in system.cell_ids]
    return {c.stage: c for c in cells}


def link_pairs(project: Project) -> set[tuple[str, str]]:
    return {(lk.source_cell_id, lk.target_cell_id) for lk in project.links}


def _set_all(project: Project, status: CellStatus) -> None:
    for cell in project.cells:
        cell.status = status


# ---------------------------------------------------------------- templates


def test_phase0_template_creates_linked_chain(project: Project) -> None:
    outcome = create_system(project, PHASE_0)
    system = project.systems[0]
    assert system.name == "Fase 0 · Viabilidad"
    assert outcome.created_ids[0] == system.id
    cells = cells_by_stage(project, system.name)
    assert [project.cells[i].stage for i in range(4)] == [
        S.MISSION,
        S.ENVIRONMENT,
        S.GLOBAL_BALANCE,
        S.TCS_CONCEPT,
    ]
    assert link_pairs(project) == {
        (cells[S.MISSION].id, cells[S.ENVIRONMENT].id),
        (cells[S.ENVIRONMENT].id, cells[S.GLOBAL_BALANCE].id),
        (cells[S.GLOBAL_BALANCE].id, cells[S.TCS_CONCEPT].id),
    }
    assert all(c.status is CellStatus.NEVER_RUN for c in project.cells)


def test_phase1_template_links_only_its_own_chain(project: Project) -> None:
    create_system(project, PHASE_1)
    assert len(project.cells) == 6
    assert len(project.links) == 5  # cross-phase inputs stay free


def test_single_stage_system(project: Project) -> None:
    create_system(project, Blueprint(stage=S.ENVIRONMENT), position=Position(x=10, y=20))
    assert project.systems[0].name == "Entorno"
    assert project.systems[0].position == Position(x=10, y=20)
    assert [c.stage for c in project.cells] == [S.ENVIRONMENT]


def test_blueprint_requires_exactly_one_source() -> None:
    with pytest.raises(ValueError):
        Blueprint()
    with pytest.raises(ValueError):
        Blueprint(template=TemplateId.PHASE_0, stage=S.MISSION)


def test_system_names_are_made_unique(project: Project) -> None:
    create_system(project, PHASE_0)
    create_system(project, PHASE_0)
    assert [s.name for s in project.systems] == ["Fase 0 · Viabilidad", "Fase 0 · Viabilidad (2)"]


def test_new_systems_do_not_overlap(project: Project) -> None:
    create_system(project, PHASE_0)
    create_system(project, PHASE_1)
    a, b = project.systems
    assert b.position.x > a.position.x


# ---------------------------------------------------------------- links


def test_valid_cross_system_link(phase0: Project) -> None:
    create_system(phase0, PHASE_1, name="F1")
    f0, f1 = cells_by_stage(phase0, "F0"), cells_by_stage(phase0, "F1")
    outcome = link(phase0, f0[S.MISSION].id, f1[S.DISCRETIZATION].id)
    new = phase0.links[-1]
    assert outcome.created_ids == [new.id]
    assert new.input is S.MISSION


def test_invalid_link_is_rejected(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    with pytest.raises(InvalidOperationError, match="no puede alimentar"):
        link(phase0, cells[S.TCS_CONCEPT].id, cells[S.MISSION].id)


def test_input_has_a_single_source(phase0: Project) -> None:
    create_system(phase0, Blueprint(stage=S.MISSION), name="M2")
    other_mission = cells_by_stage(phase0, "M2")[S.MISSION]
    environment = cells_by_stage(phase0, "F0")[S.ENVIRONMENT]
    with pytest.raises(InvalidOperationError, match="ya tiene fuente"):
        link(phase0, other_mission.id, environment.id)


def test_self_link_is_rejected(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    with pytest.raises(InvalidOperationError):
        link(phase0, mission.id, mission.id)


def test_cycle_is_rejected(project: Project) -> None:
    # Valid stage types can never form a cycle; forge a bad link to exercise the guard.
    create_system(project, Blueprint(stage=S.MISSION), name="M")
    create_system(project, Blueprint(stage=S.ENVIRONMENT), name="E")
    mission = cells_by_stage(project, "M")[S.MISSION]
    environment = cells_by_stage(project, "E")[S.ENVIRONMENT]
    project.links.append(
        Link(id="forged", source_cell_id=environment.id, target_cell_id=mission.id, input=S.MISSION)
    )
    with pytest.raises(InvalidOperationError, match="ciclo"):
        check_link(project, mission.id, environment.id)


def test_link_targets(phase0: Project) -> None:
    create_system(phase0, PHASE_1, name="F1")
    f0, f1 = cells_by_stage(phase0, "F0"), cells_by_stage(phase0, "F1")
    targets = link_targets(phase0, f0[S.MISSION].id)
    # environment already fed by this mission: only the free cross-phase inputs.
    assert set(targets) == {f1[S.DISCRETIZATION].id, f1[S.MARGINS].id}


def test_unlink_and_unknown_ids(phase0: Project) -> None:
    first = phase0.links[0]
    unlink(phase0, first.id)
    assert first not in phase0.links
    with pytest.raises(NotFoundError):
        unlink(phase0, first.id)
    with pytest.raises(NotFoundError):
        rename_cell(phase0, "cell_nope", "x")


# ---------------------------------------------------------------- outdated propagation


def test_link_change_outdates_downstream_across_systems(phase0: Project) -> None:
    create_system(phase0, PHASE_1, name="F1")
    f0, f1 = cells_by_stage(phase0, "F0"), cells_by_stage(phase0, "F1")
    link(phase0, f0[S.MISSION].id, f1[S.DISCRETIZATION].id)
    _set_all(phase0, CellStatus.UP_TO_DATE)

    env_link = next(lk for lk in phase0.links if lk.target_cell_id == f0[S.ENVIRONMENT].id)
    outcome = unlink(phase0, env_link.id)

    outdated = {c.id for c in phase0.cells if c.status is CellStatus.OUTDATED}
    assert outdated == {f0[S.ENVIRONMENT].id, f0[S.GLOBAL_BALANCE].id, f0[S.TCS_CONCEPT].id}
    assert set(outcome.outdated_cell_ids) == outdated
    assert f0[S.MISSION].status is CellStatus.UP_TO_DATE
    assert all(c.status is CellStatus.UP_TO_DATE for c in f1.values())


def test_invalidation_crosses_system_boundaries(phase0: Project) -> None:
    create_system(phase0, PHASE_1, name="F1")
    f0, f1 = cells_by_stage(phase0, "F0"), cells_by_stage(phase0, "F1")
    link(phase0, f0[S.ENVIRONMENT].id, f1[S.LOAD_CASES].id)
    _set_all(phase0, CellStatus.UP_TO_DATE)
    changed = invalidate(phase0, [f0[S.MISSION].id])
    expected = {c.id for c in f0.values()} | {
        f1[s].id for s in (S.LOAD_CASES, S.SOLUTION, S.MARGINS, S.SENSITIVITY)
    }
    assert set(changed) == expected
    assert f1[S.DISCRETIZATION].status is CellStatus.UP_TO_DATE


def test_never_run_cells_stay_never_run(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    assert invalidate(phase0, [mission.id]) == []
    assert all(c.status is CellStatus.NEVER_RUN for c in phase0.cells)


def test_failed_cells_become_outdated(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    cells[S.GLOBAL_BALANCE].status = CellStatus.FAILED
    invalidate(phase0, [cells[S.ENVIRONMENT].id])
    assert cells[S.GLOBAL_BALANCE].status is CellStatus.OUTDATED


# ---------------------------------------------------------------- add, branch


def test_add_cell_links_inside_system(project: Project) -> None:
    create_system(project, Blueprint(stage=S.MISSION), name="Sys")
    system = project.systems[0]
    add_cell(project, system.id, S.GLOBAL_BALANCE)
    outcome = add_cell(project, system.id, S.ENVIRONMENT, name="Entorno SSO")
    cells = cells_by_stage(project, "Sys")
    assert cells[S.ENVIRONMENT].name == "Entorno SSO"
    assert link_pairs(project) == {
        (cells[S.MISSION].id, cells[S.ENVIRONMENT].id),
        (cells[S.ENVIRONMENT].id, cells[S.GLOBAL_BALANCE].id),
    }
    assert cells[S.ENVIRONMENT].id in outcome.created_ids


def test_add_cell_does_not_relink_removed_links(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    removed = next(lk for lk in phase0.links if lk.target_cell_id == cells[S.ENVIRONMENT].id)
    unlink(phase0, removed.id)
    add_cell(phase0, phase0.systems[0].id, S.DISCRETIZATION)
    assert (cells[S.MISSION].id, cells[S.ENVIRONMENT].id) not in link_pairs(phase0)


def test_branch_stage_from_cell(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    outcome = branch(phase0, mission.id, Blueprint(stage=S.ENVIRONMENT), name="Entorno SSO800")
    new_system = phase0.systems[-1]
    assert new_system.name == "Entorno SSO800"
    new_env = cells_by_stage(phase0, "Entorno SSO800")[S.ENVIRONMENT]
    assert (mission.id, new_env.id) in link_pairs(phase0)
    assert new_system.id in outcome.created_ids
    # Two environments fed by the same mission.
    assert sum(1 for lk in phase0.links if lk.source_cell_id == mission.id) == 2
    assert new_system.position.x > phase0.systems[0].position.x


def test_branch_phase1_from_mission_links_all_free_inputs(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    branch(phase0, mission.id, PHASE_1)
    f1 = cells_by_stage(phase0, "Fase 1 · Modelo nodal")
    assert (mission.id, f1[S.DISCRETIZATION].id) in link_pairs(phase0)
    assert (mission.id, f1[S.MARGINS].id) in link_pairs(phase0)


def test_branch_rejects_invalid_source(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    with pytest.raises(InvalidOperationError):
        branch(phase0, mission.id, PHASE_0)  # every phase 0 input is fed internally


def test_branch_targets(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    assert branch_targets(phase0, PHASE_1) == [
        f0[S.MISSION].id,
        f0[S.ENVIRONMENT].id,
        f0[S.GLOBAL_BALANCE].id,
    ]
    assert branch_targets(phase0, PHASE_0) == []
    assert branch_targets(phase0, Blueprint(stage=S.TCS_CONCEPT)) == [f0[S.GLOBAL_BALANCE].id]
    assert branch_targets(phase0, Blueprint(stage=S.MISSION)) == []


def test_branch_options(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    options = branch_options(phase0, f0[S.MISSION].id)
    assert options == [
        PHASE_1,
        Blueprint(stage=S.ENVIRONMENT),
        Blueprint(stage=S.DISCRETIZATION),
        Blueprint(stage=S.MARGINS),
    ]
    assert branch_options(phase0, f0[S.TCS_CONCEPT].id) == []


# ---------------------------------------------------------------- rename, move, duplicate, delete


def test_rename(phase0: Project) -> None:
    system = phase0.systems[0]
    rename_system(phase0, system.id, "  Fase 0   base ")
    assert system.name == "Fase 0 base"
    cell = phase0.cells[1]
    rename_cell(phase0, cell.id, "Entorno LEO600")
    assert cell.name == "Entorno LEO600"
    with pytest.raises(InvalidOperationError):
        rename_cell(phase0, cell.id, "   ")
    with pytest.raises(InvalidOperationError):
        rename_system(phase0, system.id, "x" * 81)


def test_move_system(phase0: Project) -> None:
    move_system(phase0, phase0.systems[0].id, Position(x=100, y=-50))
    assert phase0.systems[0].position == Position(x=100, y=-50)


def test_duplicate_system_keeps_incoming_links(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    branch(phase0, mission.id, PHASE_1, name="F1")
    f1 = phase0.systems[-1]
    outcome = duplicate_system(phase0, f1.id)
    copy = phase0.systems[-1]
    assert copy.name == "F1 (copia)"
    assert copy.id in outcome.created_ids
    copied = cells_by_stage(phase0, "F1 (copia)")
    assert len(copied) == 6
    pairs = link_pairs(phase0)
    assert (mission.id, copied[S.DISCRETIZATION].id) in pairs
    assert (mission.id, copied[S.MARGINS].id) in pairs
    assert (copied[S.DISCRETIZATION].id, copied[S.COUPLINGS].id) in pairs
    assert all(c.system_id == copy.id for c in copied.values())


def test_duplicate_does_not_copy_outgoing_links(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    branch(phase0, mission.id, Blueprint(stage=S.ENVIRONMENT), name="E2")
    n_links = len(phase0.links)
    duplicate_system(phase0, phase0.systems[0].id)
    assert len(phase0.links) == n_links + 3  # only the copy's internal chain


def test_delete_cell_removes_links_and_outdates(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    _set_all(phase0, CellStatus.UP_TO_DATE)
    outcome = delete_cell(phase0, cells[S.ENVIRONMENT].id)
    assert cells[S.ENVIRONMENT].id not in {c.id for c in phase0.cells}
    assert cells[S.ENVIRONMENT].id not in phase0.systems[0].cell_ids
    assert len(phase0.links) == 1
    assert set(outcome.outdated_cell_ids) == {cells[S.GLOBAL_BALANCE].id, cells[S.TCS_CONCEPT].id}


def test_deleting_last_cell_deletes_system(project: Project) -> None:
    create_system(project, Blueprint(stage=S.MISSION))
    outcome = delete_cell(project, project.cells[0].id)
    assert project.systems == []
    assert "sistema vacío" in outcome.summary


def test_delete_system_outdates_other_systems(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    branch(phase0, mission.id, PHASE_1, name="F1")
    _set_all(phase0, CellStatus.UP_TO_DATE)
    outcome = delete_system(phase0, phase0.systems[0].id)
    assert [s.name for s in phase0.systems] == ["F1"]
    assert len(phase0.cells) == 6
    assert all(c.status is CellStatus.OUTDATED for c in phase0.cells)
    assert len(outcome.outdated_cell_ids) == 6
    assert all(lk.source_cell_id in {c.id for c in phase0.cells} for lk in phase0.links)
