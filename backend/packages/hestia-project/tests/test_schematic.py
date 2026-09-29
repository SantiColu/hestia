"""Schematic rules (docs/workflow-fases-0-1.md, ADR 0016), with the examples of the doc."""

from itertools import pairwise

import pytest

from hestia_project.catalog import STAGES, StageKind, StageSpec, StageType, TemplateId
from hestia_project.errors import InvalidOperationError, NotFoundError
from hestia_project.model import Cell, CellStatus, Link, Position, Project
from hestia_project.schematic import (
    Blueprint,
    add_cell,
    branch,
    branch_options,
    branch_targets,
    cell_context,
    check_link,
    context_cells,
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


def single(project: Project, stage: StageType, name: str | None = None) -> Cell:
    """Create a system with one cell and return the cell."""
    create_system(project, Blueprint(stage=stage), name=name)
    return project.cells[-1]


def link_pairs(project: Project) -> set[tuple[str, str]]:
    return {(lk.source_cell_id, lk.target_cell_id) for lk in project.links}


def rule_of(project: Project, source: Cell, target: Cell) -> str:
    with pytest.raises(InvalidOperationError) as info:
        check_link(project, source.id, target.id)
    return info.value.details["rule"]


def _set_all(project: Project, status: CellStatus) -> None:
    for cell in project.cells:
        cell.status = status


# ---------------------------------------------------------------- templates


def test_phase0_template_creates_five_cells_joined_at_the_balance(project: Project) -> None:
    outcome = create_system(project, PHASE_0)
    system = project.systems[0]
    assert system.name == "Fase 0 · Viabilidad"
    assert outcome.created_ids[0] == system.id
    assert [project.cells[i].stage for i in range(5)] == [
        S.MISSION,
        S.ENVIRONMENT,
        S.EQUIPMENT,
        S.GLOBAL_BALANCE,
        S.TCS_CONCEPT,
    ]
    c = cells_by_stage(project, system.name)
    assert link_pairs(project) == {
        (c[S.MISSION].id, c[S.ENVIRONMENT].id),
        (c[S.ENVIRONMENT].id, c[S.GLOBAL_BALANCE].id),
        (c[S.EQUIPMENT].id, c[S.GLOBAL_BALANCE].id),
        (c[S.GLOBAL_BALANCE].id, c[S.TCS_CONCEPT].id),
    }
    assert all(c.status is CellStatus.NEVER_RUN for c in project.cells)
    # Every requirement of phase 0 is covered inside the template.
    assert all(cell_context(project, cell.id).missing == [] for cell in project.cells)


def test_phase1_template_is_a_linear_chain(project: Project) -> None:
    create_system(project, PHASE_1)
    assert len(project.cells) == 6
    ids = [c.id for c in project.cells]
    assert link_pairs(project) == set(pairwise(ids))
    discretization = project.cells[0]
    assert cell_context(project, discretization.id).missing == [
        S.MISSION,
        S.EQUIPMENT,
        S.TCS_CONCEPT,
    ]


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


# ---------------------------------------------------------------- context


def test_context_is_everything_upstream_by_type(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    context = cell_context(phase0, f0[S.TCS_CONCEPT].id)
    assert [(e.stage, e.cell_id) for e in context.entries] == [
        (S.MISSION, f0[S.MISSION].id),
        (S.ENVIRONMENT, f0[S.ENVIRONMENT].id),
        (S.EQUIPMENT, f0[S.EQUIPMENT].id),
        (S.GLOBAL_BALANCE, f0[S.GLOBAL_BALANCE].id),
    ]
    assert context.missing == []
    assert cell_context(phase0, f0[S.MISSION].id).entries == []


def test_one_link_between_phases_is_enough(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    branch(phase0, f0[S.TCS_CONCEPT].id, PHASE_1, name="F1")
    f1 = cells_by_stage(phase0, "F1")
    assert len(phase0.links) == 4 + 5 + 1
    for cell in f1.values():
        assert cell_context(phase0, cell.id).missing == [], cell.stage
    margins = cell_context(phase0, f1[S.MARGINS].id)
    provider = {e.stage: e.cell_id for e in margins.entries}
    assert provider[S.MISSION] == f0[S.MISSION].id
    assert provider[S.SOLUTION] == f1[S.SOLUTION].id


def test_missing_requirements_do_not_block_links(project: Project) -> None:
    # «mission → global_balance es válido; la celda queda con missing [environment, equipment]».
    mission = single(project, S.MISSION)
    balance = single(project, S.GLOBAL_BALANCE)
    link(project, mission.id, balance.id)
    assert cell_context(project, balance.id).missing == [S.ENVIRONMENT, S.EQUIPMENT]
    # Completed by union with equipment.
    equipment = single(project, S.EQUIPMENT)
    link(project, equipment.id, balance.id)
    assert cell_context(project, balance.id).missing == [S.ENVIRONMENT]


def test_variants_share_roots(project: Project) -> None:
    # Two environments can use the same equipment cell.
    mission = single(project, S.MISSION)
    equipment = single(project, S.EQUIPMENT)
    balances: list[Cell] = []
    for name in ("LEO", "SSO"):
        env = single(project, S.ENVIRONMENT, name=f"Entorno {name}")
        link(project, mission.id, env.id)
        balance = single(project, S.GLOBAL_BALANCE, name=f"Balance {name}")
        link(project, env.id, balance.id)
        link(project, equipment.id, balance.id)
        balances.append(balance)
    for balance in balances:
        by_type = context_cells(project, balance.id)
        assert by_type[S.EQUIPMENT] == [equipment.id]
        assert by_type[S.MISSION] == [mission.id]
        assert cell_context(project, balance.id).missing == []


# ---------------------------------------------------------------- link rules


def test_rule1_cycle(project: Project) -> None:
    # Valid links can never form a cycle; forge one to exercise the guard.
    environment = single(project, S.ENVIRONMENT)
    balance = single(project, S.GLOBAL_BALANCE)
    project.links.append(
        Link(id="forged", source_cell_id=balance.id, target_cell_id=environment.id)
    )
    assert rule_of(project, environment, balance) == "cycle"
    assert rule_of(project, environment, environment) == "cycle"


def test_rule2_roots_have_no_parents(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    assert rule_of(phase0, f0[S.ENVIRONMENT], f0[S.MISSION]) == "root"
    assert rule_of(phase0, f0[S.MISSION], f0[S.EQUIPMENT]) == "root"


def test_rule3_second_parent_only_by_union(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    other_mission = single(phase0, S.MISSION, name="M2")
    # environment already has a mission parent.
    assert rule_of(phase0, other_mission, f0[S.ENVIRONMENT]) == "parents"
    # The balance already has mission (through environment): a second mission cannot join.
    assert rule_of(phase0, other_mission, f0[S.GLOBAL_BALANCE]) == "parents"
    # A second equipment list cannot join either.
    other_equipment = single(phase0, S.EQUIPMENT, name="E2")
    with pytest.raises(InvalidOperationError, match="unión"):
        check_link(phase0, other_equipment.id, f0[S.GLOBAL_BALANCE].id)


def test_rule3_union_with_disjoint_contexts(project: Project) -> None:
    mission = single(project, S.MISSION)
    environment = single(project, S.ENVIRONMENT)
    link(project, mission.id, environment.id)
    balance = single(project, S.GLOBAL_BALANCE)
    link(project, mission.id, balance.id)
    # environment brings mission again: not a union.
    assert rule_of(project, environment, balance) == "parents"


def test_rule4_no_repeats_downstream(project: Project) -> None:
    # load_cases joins couplings (discretization chain) and environment (with mission). Feeding a
    # second mission into discretization would repeat mission in load_cases.
    m1, m2 = single(project, S.MISSION, "M1"), single(project, S.MISSION, "M2")
    environment = single(project, S.ENVIRONMENT)
    link(project, m1.id, environment.id)
    discretization = single(project, S.DISCRETIZATION)
    couplings = single(project, S.COUPLINGS)
    link(project, discretization.id, couplings.id)
    load_cases = single(project, S.LOAD_CASES)
    link(project, couplings.id, load_cases.id)
    link(project, environment.id, load_cases.id)
    with pytest.raises(InvalidOperationError, match="aguas abajo") as info:
        check_link(project, m2.id, discretization.id)
    assert info.value.details["rule"] == "repeat"
    # Feeding the same mission is fine: it is the same cell, not a repeat.
    link(project, m1.id, discretization.id)
    assert context_cells(project, load_cases.id)[S.MISSION] == [m1.id]


def test_rule4_own_type(project: Project) -> None:
    b1, b2 = single(project, S.GLOBAL_BALANCE, "B1"), single(project, S.GLOBAL_BALANCE, "B2")
    assert rule_of(project, b1, b2) == "repeat"


def test_rule5_catalog_order(project: Project) -> None:
    equipment = single(project, S.EQUIPMENT)
    environment = single(project, S.ENVIRONMENT)
    assert rule_of(project, equipment, environment) == "order"
    concept = single(project, S.TCS_CONCEPT)
    balance = single(project, S.GLOBAL_BALANCE)
    assert rule_of(project, concept, balance) == "order"


def test_duplicate_link_is_rejected(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    assert rule_of(phase0, f0[S.MISSION], f0[S.ENVIRONMENT]) == "duplicate"


def test_collectors(project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
    # No collector exists yet (comparison is future): make sensitivity one for this test.
    spec = STAGES[S.SENSITIVITY]
    monkeypatch.setitem(
        STAGES,
        S.SENSITIVITY,
        StageSpec(
            spec.stage,
            spec.phase,
            spec.number,
            spec.default_name,
            StageKind.COLLECTOR,
            False,
            (),
            False,
        ),
    )
    m1, m2 = single(project, S.MISSION, "M1"), single(project, S.MISSION, "M2")
    collector = single(project, S.SENSITIVITY)
    link(project, m1.id, collector.id)
    link(project, m2.id, collector.id)  # several parents of the same type
    assert context_cells(project, collector.id)[S.MISSION] == [m1.id, m2.id] or context_cells(
        project, collector.id
    )[S.MISSION] == [m2.id, m1.id]
    # Terminal: passes no context downstream.
    other = single(project, S.SENSITIVITY, "Otra")
    assert rule_of(project, collector, other) == "collector"


def test_link_targets(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    create_system(phase0, PHASE_1, name="F1")
    f1 = cells_by_stage(phase0, "F1")
    phase1 = [c.id for c in f1.values()]
    # Phase 0 feeds discretization (no parent) or any other phase 1 cell by union: their
    # contexts share no type.
    assert link_targets(phase0, f0[S.MISSION].id) == phase1
    assert link_targets(phase0, f0[S.TCS_CONCEPT].id) == phase1
    # Once the concept feeds discretization, the chain already has mission in its context.
    link(phase0, f0[S.TCS_CONCEPT].id, f1[S.DISCRETIZATION].id)
    assert link_targets(phase0, f0[S.MISSION].id) == []
    assert link_targets(phase0, f1[S.SENSITIVITY].id) == []


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
    f0 = cells_by_stage(phase0, "F0")
    branch(phase0, f0[S.TCS_CONCEPT].id, PHASE_1, name="F1")
    f1 = cells_by_stage(phase0, "F1")
    _set_all(phase0, CellStatus.UP_TO_DATE)

    env_link = next(lk for lk in phase0.links if lk.target_cell_id == f0[S.ENVIRONMENT].id)
    outcome = unlink(phase0, env_link.id)

    outdated = {c.id for c in phase0.cells if c.status is CellStatus.OUTDATED}
    expected = {f0[s].id for s in (S.ENVIRONMENT, S.GLOBAL_BALANCE, S.TCS_CONCEPT)} | {
        c.id for c in f1.values()
    }
    assert outdated == expected
    assert set(outcome.outdated_cell_ids) == outdated
    assert f0[S.MISSION].status is CellStatus.UP_TO_DATE
    assert f0[S.EQUIPMENT].status is CellStatus.UP_TO_DATE


def test_form_stages_are_not_outdated(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    _set_all(phase0, CellStatus.UP_TO_DATE)
    changed = invalidate(phase0, [f0[S.MISSION].id])
    assert f0[S.MISSION].status is CellStatus.UP_TO_DATE
    assert set(changed) == {f0[s].id for s in (S.ENVIRONMENT, S.GLOBAL_BALANCE, S.TCS_CONCEPT)}


def test_never_run_cells_stay_never_run(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    assert invalidate(phase0, [mission.id]) == []
    assert all(c.status is CellStatus.NEVER_RUN for c in phase0.cells)


def test_failed_cells_become_outdated(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    cells[S.GLOBAL_BALANCE].status = CellStatus.FAILED
    invalidate(phase0, [cells[S.ENVIRONMENT].id])
    assert cells[S.GLOBAL_BALANCE].status is CellStatus.OUTDATED


# ---------------------------------------------------------------- add cell (autolink)


def test_add_cell_takes_equipment_then_environment(project: Project) -> None:
    # «global_balance en un sistema con misión, ambiente y equipos toma equipment y después
    # environment (unión)».
    create_system(project, Blueprint(stage=S.MISSION), name="Sys")
    system = project.systems[0]
    add_cell(project, system.id, S.ENVIRONMENT)
    add_cell(project, system.id, S.EQUIPMENT)
    outcome = add_cell(project, system.id, S.GLOBAL_BALANCE)
    c = cells_by_stage(project, "Sys")
    new_links = [lk for lk in project.links if lk.target_cell_id == c[S.GLOBAL_BALANCE].id]
    assert [lk.source_cell_id for lk in new_links] == [c[S.EQUIPMENT].id, c[S.ENVIRONMENT].id]
    assert all(lk.id in outcome.created_ids for lk in new_links)
    assert cell_context(project, c[S.GLOBAL_BALANCE].id).missing == []


def test_add_cell_as_source(project: Project) -> None:
    create_system(project, Blueprint(stage=S.ENVIRONMENT), name="Sys")
    system = project.systems[0]
    add_cell(project, system.id, S.MISSION, name="Misión SSO")
    c = cells_by_stage(project, "Sys")
    assert c[S.MISSION].name == "Misión SSO"
    assert link_pairs(project) == {(c[S.MISSION].id, c[S.ENVIRONMENT].id)}


def test_add_cell_outdates_the_cells_it_feeds(project: Project) -> None:
    create_system(project, Blueprint(stage=S.ENVIRONMENT), name="Sys")
    environment = project.cells[0]
    environment.status = CellStatus.UP_TO_DATE
    outcome = add_cell(project, project.systems[0].id, S.MISSION)
    assert outcome.outdated_cell_ids == [environment.id]


def test_add_cell_links_only_what_brings_requirements(project: Project) -> None:
    # A lone mission does not feed a concept: it brings nothing the concept requires.
    create_system(project, Blueprint(stage=S.MISSION), name="Sys")
    add_cell(project, project.systems[0].id, S.TCS_CONCEPT)
    assert project.links == []


def test_add_cell_does_not_relink_removed_links(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    removed = next(lk for lk in phase0.links if lk.target_cell_id == cells[S.ENVIRONMENT].id)
    unlink(phase0, removed.id)
    add_cell(phase0, phase0.systems[0].id, S.DISCRETIZATION)
    assert (cells[S.MISSION].id, cells[S.ENVIRONMENT].id) not in link_pairs(phase0)
    discretization = cells_by_stage(phase0, "F0")[S.DISCRETIZATION]
    # Takes the concept (with equipment) and then the mission, by union.
    assert cell_context(phase0, discretization.id).missing == []


# ---------------------------------------------------------------- branch


def test_branch_phase1_from_concept_links_discretization(phase0: Project) -> None:
    concept = cells_by_stage(phase0, "F0")[S.TCS_CONCEPT]
    outcome = branch(phase0, concept.id, PHASE_1)
    f1 = cells_by_stage(phase0, "Fase 1 · Modelo nodal")
    assert (concept.id, f1[S.DISCRETIZATION].id) in link_pairs(phase0)
    assert sum(1 for lk in phase0.links if lk.source_cell_id == concept.id) == 1
    assert phase0.systems[-1].id in outcome.created_ids


def test_branch_environment_from_mission_is_a_variant(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    branch(phase0, mission.id, Blueprint(stage=S.ENVIRONMENT), name="Entorno SSO800")
    new_system = phase0.systems[-1]
    new_env = cells_by_stage(phase0, "Entorno SSO800")[S.ENVIRONMENT]
    assert (mission.id, new_env.id) in link_pairs(phase0)
    assert sum(1 for lk in phase0.links if lk.source_cell_id == mission.id) == 2
    assert new_system.position.x > phase0.systems[0].position.x


def test_branch_phase0_is_never_valid(phase0: Project) -> None:
    for cell in list(phase0.cells):
        with pytest.raises(InvalidOperationError, match="ninguna de sus celdas"):
            branch(phase0, cell.id, PHASE_0)
    assert branch_targets(phase0, PHASE_0) == []


def test_branch_targets(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    ordered = [c.id for c in phase0.cells]
    assert branch_targets(phase0, PHASE_1) == ordered
    assert branch_targets(phase0, Blueprint(stage=S.TCS_CONCEPT)) == [
        f0[s].id for s in (S.MISSION, S.ENVIRONMENT, S.EQUIPMENT, S.GLOBAL_BALANCE)
    ]
    assert branch_targets(phase0, Blueprint(stage=S.MISSION)) == []
    assert branch_targets(phase0, Blueprint(stage=S.EQUIPMENT)) == []
    # Branching does not change the project.
    assert len(phase0.systems) == 1


def test_branch_options(phase0: Project) -> None:
    f0 = cells_by_stage(phase0, "F0")
    after_concept = [
        S.DISCRETIZATION,
        S.COUPLINGS,
        S.LOAD_CASES,
        S.SOLUTION,
        S.MARGINS,
        S.SENSITIVITY,
    ]
    assert branch_options(phase0, f0[S.TCS_CONCEPT].id) == [
        PHASE_1,
        *(Blueprint(stage=s) for s in after_concept),
    ]
    assert branch_options(phase0, f0[S.MISSION].id) == [
        PHASE_1,
        *(
            Blueprint(stage=s)
            for s in (S.ENVIRONMENT, S.GLOBAL_BALANCE, S.TCS_CONCEPT, *after_concept)
        ),
    ]


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
    concept = cells_by_stage(phase0, "F0")[S.TCS_CONCEPT]
    branch(phase0, concept.id, PHASE_1, name="F1")
    f1 = phase0.systems[-1]
    f1_cells = cells_by_stage(phase0, "F1")
    f1_cells[S.COUPLINGS].status = CellStatus.FAILED
    outcome = duplicate_system(phase0, f1.id)
    copy = phase0.systems[-1]
    assert copy.name == "F1 (copia)"
    assert copy.id in outcome.created_ids
    copied = cells_by_stage(phase0, "F1 (copia)")
    assert len(copied) == 6
    pairs = link_pairs(phase0)
    assert (concept.id, copied[S.DISCRETIZATION].id) in pairs
    assert (copied[S.DISCRETIZATION].id, copied[S.COUPLINGS].id) in pairs
    assert all(c.system_id == copy.id for c in copied.values())
    assert copied[S.COUPLINGS].status is CellStatus.FAILED
    assert cell_context(phase0, copied[S.SENSITIVITY].id).missing == []


def test_duplicate_does_not_copy_outgoing_links(phase0: Project) -> None:
    mission = cells_by_stage(phase0, "F0")[S.MISSION]
    branch(phase0, mission.id, Blueprint(stage=S.ENVIRONMENT), name="E2")
    n_links = len(phase0.links)
    duplicate_system(phase0, phase0.systems[0].id)
    assert len(phase0.links) == n_links + 4  # only the copy's internal links


def test_delete_cell_removes_links_and_outdates(phase0: Project) -> None:
    cells = cells_by_stage(phase0, "F0")
    _set_all(phase0, CellStatus.UP_TO_DATE)
    outcome = delete_cell(phase0, cells[S.ENVIRONMENT].id)
    assert cells[S.ENVIRONMENT].id not in {c.id for c in phase0.cells}
    assert cells[S.ENVIRONMENT].id not in phase0.systems[0].cell_ids
    assert len(phase0.links) == 2
    assert set(outcome.outdated_cell_ids) == {cells[S.GLOBAL_BALANCE].id, cells[S.TCS_CONCEPT].id}
    assert cell_context(phase0, cells[S.GLOBAL_BALANCE].id).missing == [
        S.MISSION,
        S.ENVIRONMENT,
    ]


def test_deleting_last_cell_deletes_system(project: Project) -> None:
    create_system(project, Blueprint(stage=S.MISSION))
    outcome = delete_cell(project, project.cells[0].id)
    assert project.systems == []
    assert "sistema vacío" in outcome.summary


def test_delete_system_outdates_other_systems(phase0: Project) -> None:
    concept = cells_by_stage(phase0, "F0")[S.TCS_CONCEPT]
    branch(phase0, concept.id, PHASE_1, name="F1")
    _set_all(phase0, CellStatus.UP_TO_DATE)
    outcome = delete_system(phase0, phase0.systems[0].id)
    assert [s.name for s in phase0.systems] == ["F1"]
    assert len(phase0.cells) == 6
    assert all(c.status is CellStatus.OUTDATED for c in phase0.cells)
    assert len(outcome.outdated_cell_ids) == 6
    assert all(lk.source_cell_id in {c.id for c in phase0.cells} for lk in phase0.links)
