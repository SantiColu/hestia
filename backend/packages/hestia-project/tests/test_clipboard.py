from pathlib import Path

import pytest
from pydantic import ValidationError

from hestia_project.catalog import StageType, TemplateId
from hestia_project.clipboard import (
    FRAGMENT_KIND,
    PASTE_OFFSET,
    Fragment,
    FragmentCell,
    FragmentLink,
    FragmentSystem,
    copy,
    paste,
)
from hestia_project.document import ProjectDocument
from hestia_project.errors import InvalidFragmentError, InvalidOperationError, NotFoundError
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import CellStatus, Position, Project, System
from hestia_project.schematic import Blueprint, branch, create_system
from hestia_project.storage import read_project, write_project

S = StageType
AGENT = Author(kind=ActorKind.AGENT, name="stefan")


def _system(project: Project, name: str) -> System:
    return next(s for s in project.systems if s.name == name)


def _stages(project: Project, name: str) -> list[StageType]:
    system = _system(project, name)
    by_id = {c.id: c for c in project.cells}
    return [by_id[cid].stage for cid in system.cell_ids]


def _pairs(project: Project, system_names: set[str]) -> set[tuple[StageType, StageType]]:
    ids = {cid for s in project.systems if s.name in system_names for cid in s.cell_ids}
    by_id = {c.id: c for c in project.cells}
    return {
        (by_id[lk.source_cell_id].stage, by_id[lk.target_cell_id].stage)
        for lk in project.links
        if lk.source_cell_id in ids and lk.target_cell_id in ids
    }


# ---------------------------------------------------------------- copy


def test_copy_system_snapshots_cells_and_internal_links(phase0: Project) -> None:
    before = phase0.model_copy(deep=True)
    fragment = copy(phase0, [phase0.systems[0].id], [])
    assert phase0 == before
    assert fragment.kind == FRAGMENT_KIND
    assert fragment.schema_version == 1
    assert fragment.source_project_id == phase0.id
    [system] = fragment.systems
    assert system.whole and system.name == "F0"
    assert [c.stage for c in system.cells] == [
        S.MISSION,
        S.ENVIRONMENT,
        S.GLOBAL_BALANCE,
        S.TCS_CONCEPT,
    ]
    assert len(fragment.links) == 3


def test_copy_cell_keeps_only_links_inside_the_fragment(phase0: Project) -> None:
    env = next(c for c in phase0.cells if c.stage is S.ENVIRONMENT)
    fragment = copy(phase0, [], [env.id])
    [system] = fragment.systems
    assert not system.whole
    assert [c.id for c in system.cells] == [env.id]
    assert fragment.links == []


def test_copy_skips_cells_of_systems_copied_whole(phase0: Project) -> None:
    fragment = copy(phase0, [phase0.systems[0].id], [phase0.cells[0].id])
    assert len(fragment.systems) == 1


def test_copy_needs_something_and_existing_ids(phase0: Project) -> None:
    with pytest.raises(InvalidOperationError):
        copy(phase0, [], [])
    with pytest.raises(NotFoundError):
        copy(phase0, ["nope"], [])


# ---------------------------------------------------------------- paste


def test_paste_system_creates_new_ids_and_internal_links(phase0: Project) -> None:
    fragment = copy(phase0, [phase0.systems[0].id], [])
    old_ids = {c.id for c in phase0.cells} | {s.id for s in phase0.systems}
    outcome = paste(phase0, fragment)
    assert len(phase0.systems) == 2
    pasted = _system(phase0, "F0 (2)")
    assert pasted.id not in old_ids
    assert not set(pasted.cell_ids) & old_ids
    assert _stages(phase0, "F0 (2)") == _stages(phase0, "F0")
    assert _pairs(phase0, {"F0 (2)"}) == _pairs(phase0, {"F0"})
    assert outcome.created_ids[0] == pasted.id
    assert len(outcome.created_ids) == 1 + 4 + 3
    assert outcome.summary == "Pegó el sistema «F0 (2)»."


def test_pasted_cells_are_never_run(phase0: Project) -> None:
    for cell in phase0.cells:
        cell.status = CellStatus.UP_TO_DATE
    paste(phase0, copy(phase0, [phase0.systems[0].id], []))
    pasted = _system(phase0, "F0 (2)")
    assert all(
        c.status is CellStatus.NEVER_RUN and c.provenance is None
        for c in phase0.cells
        if c.id in pasted.cell_ids
    )


def test_external_links_are_dropped(phase0: Project) -> None:
    mission = phase0.cells[0]
    branch(phase0, mission.id, Blueprint(stage=S.ENVIRONMENT), name="SSO")
    fed = _system(phase0, "SSO")
    n_links = len(phase0.links)
    paste(phase0, copy(phase0, [fed.id], []))
    # The copy of SSO is not fed by the mission: incoming links are not part of the fragment.
    assert len(phase0.links) == n_links
    copy_cell = _system(phase0, "SSO (2)").cell_ids[0]
    assert not any(lk.target_cell_id == copy_cell for lk in phase0.links)


def test_names_in_conflict_get_a_suffix(phase0: Project) -> None:
    fragment = copy(phase0, [phase0.systems[0].id], [])
    paste(phase0, fragment)
    paste(phase0, fragment)
    assert [s.name for s in phase0.systems] == ["F0", "F0 (2)", "F0 (3)"]


def test_paste_cell_into_target_system(phase0: Project) -> None:
    system = phase0.systems[0]
    mission = phase0.cells[0]
    outcome = paste(phase0, copy(phase0, [], [mission.id]), target_system_id=system.id)
    assert len(phase0.systems) == 1
    assert len(system.cell_ids) == 5
    names = [c.name for c in phase0.cells if c.system_id == system.id]
    assert names[-1] == f"{mission.name} (2)"
    assert outcome.summary == "Pegó la celda en el sistema «F0»."


def test_paste_single_cell_without_target_creates_a_system_named_after_it(
    phase0: Project,
) -> None:
    env = next(c for c in phase0.cells if c.stage is S.ENVIRONMENT)
    paste(phase0, copy(phase0, [], [env.id]))
    new = phase0.systems[-1]
    assert new.name == env.name
    assert _stages(phase0, new.name) == [S.ENVIRONMENT]


def test_paste_position_keeps_relative_layout(project: Project) -> None:
    create_system(project, Blueprint(stage=S.MISSION), name="A", position=Position(x=100, y=50))
    create_system(project, Blueprint(stage=S.MISSION), name="B", position=Position(x=500, y=150))
    fragment = copy(project, [s.id for s in project.systems], [])
    paste(project, fragment, position=Position(x=1000, y=1000))
    assert _system(project, "A (2)").position == Position(x=1000, y=1000)
    assert _system(project, "B (2)").position == Position(x=1400, y=1100)


def test_paste_without_position_shifts_from_the_original(project: Project) -> None:
    create_system(project, Blueprint(stage=S.MISSION), name="A", position=Position(x=0, y=0))
    paste(project, copy(project, [project.systems[0].id], []))
    pos = _system(project, "A (2)").position
    assert pos.x == PASTE_OFFSET and pos.y > 0  # shifted, then moved down to avoid overlap


def test_paste_into_another_project(phase0: Project) -> None:
    other = Project(id="other", name="other")
    paste(other, copy(phase0, [phase0.systems[0].id], []))
    assert [s.name for s in other.systems] == ["F0"]
    assert len(other.cells) == 4 and len(other.links) == 3


# ---------------------------------------------------------------- invalid fragments


def _fragment(**update: object) -> Fragment:
    base = Fragment(
        source_project_id="p",
        systems=[
            FragmentSystem(
                name="X",
                position=Position(x=0, y=0),
                whole=True,
                cells=[
                    FragmentCell(id="a", stage=S.MISSION, name="Misión"),
                    FragmentCell(id="b", stage=S.ENVIRONMENT, name="Entorno"),
                ],
            )
        ],
        links=[FragmentLink(source_cell_id="a", target_cell_id="b")],
    )
    return base.model_copy(update=update)


def test_valid_handmade_fragment(project: Project) -> None:
    paste(project, _fragment())
    assert len(project.links) == 1


def test_unknown_version_is_rejected(project: Project) -> None:
    with pytest.raises(InvalidFragmentError, match="versión 99"):
        paste(project, _fragment(schema_version=99))
    assert project.systems == []


def test_wrong_kind_is_rejected() -> None:
    data = _fragment().model_dump(mode="json")
    data["kind"] = "something.else"
    with pytest.raises(ValidationError):
        Fragment.model_validate(data)


def test_link_outside_the_fragment_is_rejected(project: Project) -> None:
    with pytest.raises(InvalidFragmentError):
        paste(project, _fragment(links=[FragmentLink(source_cell_id="a", target_cell_id="z")]))


def test_invalid_link_is_rejected(project: Project) -> None:
    with pytest.raises(InvalidFragmentError, match="vínculo inválido"):
        paste(project, _fragment(links=[FragmentLink(source_cell_id="b", target_cell_id="a")]))


def test_empty_fragment_is_rejected(project: Project) -> None:
    with pytest.raises(InvalidFragmentError):
        paste(project, _fragment(systems=[]))


def test_missing_target_system(project: Project) -> None:
    with pytest.raises(NotFoundError):
        paste(project, _fragment(), target_system_id="nope")


# ---------------------------------------------------------------- history and file


def _doc_with_paste() -> ProjectDocument:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        AGENT,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0), name="F0"),
    )
    fragment = copy(doc.project, [doc.project.systems[0].id], [])
    doc.apply(Operation.PASTE, AGENT, "variant", lambda p: paste(p, fragment))
    return doc


def test_paste_is_one_undoable_change_with_author() -> None:
    doc = _doc_with_paste()
    change = doc.changes()[-1]
    assert change.operation is Operation.PASTE
    assert change.author == AGENT and change.justification == "variant"
    assert doc.state().undo_label == "pegar"
    after = doc.project.model_copy(deep=True)
    doc.undo(AGENT)
    assert [s.name for s in doc.project.systems] == ["F0"]
    assert len(doc.project.cells) == 4
    assert doc.state().redo_label == "pegar"
    doc.redo(AGENT)
    assert doc.project == after


def test_paste_survives_save_and_open(tmp_path: Path) -> None:
    doc = _doc_with_paste()
    path = tmp_path / "sat.hestia"
    write_project(path, doc.project, doc.history)
    project, history = read_project(path)
    assert project == doc.project
    assert history[-1].change.operation is Operation.PASTE


def test_summary_of_mixed_paste(phase0: Project) -> None:
    system = phase0.systems[0]
    create_system(phase0, Blueprint(stage=S.MISSION), name="M")
    other = _system(phase0, "M")
    fragment = copy(phase0, [system.id], [other.cell_ids[0]])
    outcome = paste(phase0, fragment, target_system_id=other.id)
    assert outcome.summary == "Pegó el sistema «F0 (2)» y la celda en el sistema «M»."
    outcome = paste(phase0, copy(phase0, [system.id, other.id], []))
    assert outcome.summary == "Pegó 2 sistemas con 6 celdas."
