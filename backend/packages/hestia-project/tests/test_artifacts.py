"""Form stage artifacts (ADR 0017): defaults, dry validation, apply, provenance, state."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from hestia_core.forms import ProblemCode
from hestia_core.mission import MissionArtifact
from hestia_project.artifacts import (
    CellArtifact,
    NoChange,
    apply_artifact,
    assign_ids,
    read_artifact,
    validate_draft,
)
from hestia_project.catalog import StageType, TemplateId
from hestia_project.clipboard import copy, paste
from hestia_project.document import ProjectDocument
from hestia_project.errors import JustificationRequiredError, StageNotImplementedError
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import Cell, CellStatus, FieldSource, Project
from hestia_project.schematic import Blueprint, create_system, duplicate_system
from hestia_project.storage import read_project, read_project_file, write_project

S = StageType
HUMAN = Author(kind=ActorKind.HUMAN, name="ana")
AGENT = Author(kind=ActorKind.AGENT, name="stefan")

VALID: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 157_788_000.0},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
}


def mission_of(view: CellArtifact) -> MissionArtifact:
    assert isinstance(view.artifact, MissionArtifact)
    return view.artifact


def draft(**sections: Any) -> MissionArtifact:
    return MissionArtifact.model_validate({**VALID, **sections})


def doc_with_phase0() -> ProjectDocument:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0), name="F0"),
    )
    return doc


def cell_of(project: Project, stage: StageType) -> Cell:
    return next(c for c in project.cells if c.stage is stage)


def apply(doc: ProjectDocument, artifact: MissionArtifact, why: str = "datos del cliente") -> str:
    mission = cell_of(doc.project, S.MISSION)
    return doc.apply(
        Operation.APPLY_ARTIFACT, AGENT, why, lambda p: apply_artifact(p, mission.id, artifact)
    ).id


# ---------------------------------------------------------------- defaults and reading


def test_new_mission_cell_has_library_defaults() -> None:
    doc = doc_with_phase0()
    created = doc.changes()[0]
    mission = cell_of(doc.project, S.MISSION)
    view = read_artifact(doc.project, mission.id)
    assert mission.status is CellStatus.NEVER_RUN and not view.applied
    assert mission_of(view).criteria.uncertainty_margin == 10.0
    assert set(view.provenance) == {
        "criteria.uncertainty_margin",
        "criteria.acceptance_margin",
        "criteria.qualification_margin",
    }
    assert all(p.source is FieldSource.DEFAULT for p in view.provenance.values())
    assert all(p.change_id == created.id for p in view.provenance.values())
    assert {p.path for p in view.problems} >= {"general.launch_date", "envelope.mass"}
    assert view.context.entries == [] and view.context.missing == []


def test_other_stages_have_no_artifact() -> None:
    doc = doc_with_phase0()
    for stage in (S.EQUIPMENT, S.GLOBAL_BALANCE):
        cell = cell_of(doc.project, stage)
        assert cell.form is None
        with pytest.raises(StageNotImplementedError):
            read_artifact(doc.project, cell.id)
        with pytest.raises(StageNotImplementedError):
            apply_artifact(doc.project, cell.id, draft())


# ---------------------------------------------------------------- dry validation


def test_dry_validation_changes_nothing() -> None:
    doc = doc_with_phase0()
    before = doc.project.model_copy(deep=True)
    mission = cell_of(doc.project, S.MISSION)
    problems = validate_draft(
        doc.project, mission.id, draft(envelope={"size_x": 0, "size_y": 1.0, "size_z": 1.0})
    ).problems
    assert [(p.path, p.code) for p in problems] == [
        ("envelope.size_x", ProblemCode.MIN),
        ("envelope.mass", ProblemCode.REQUIRED),
    ]
    assert validate_draft(doc.project, mission.id, draft()).problems == []
    assert doc.project == before
    assert doc.revision == 1


def test_stages_without_derived_values_return_none() -> None:
    doc = doc_with_phase0()
    for stage in (S.MISSION, S.ENVIRONMENT):
        cell = cell_of(doc.project, stage)
        assert read_artifact(doc.project, cell.id).derived is None
        draft_of = read_artifact(doc.project, cell.id).artifact
        assert validate_draft(doc.project, cell.id, draft_of).derived is None


# ---------------------------------------------------------------- apply


def test_apply_is_one_change_with_justification() -> None:
    doc = doc_with_phase0()
    with pytest.raises(JustificationRequiredError):
        apply(doc, draft(), why="  ")
    change_id = apply(doc, draft())
    change = doc.changes()[-1]
    assert change.id == change_id and change.operation is Operation.APPLY_ARTIFACT
    assert change.author == AGENT and change.justification == "datos del cliente"
    assert "Aplicó «Misión»" in change.summary
    assert doc.state().undo_label == "aplicar cambios"
    mission = cell_of(doc.project, S.MISSION)
    assert mission.status is CellStatus.UP_TO_DATE
    assert mission.form is not None and mission.form.problems == []


def test_apply_with_problems_leaves_the_cell_failed() -> None:
    doc = doc_with_phase0()
    apply(doc, draft(envelope={"size_x": 1.0}))
    view = read_artifact(doc.project, cell_of(doc.project, S.MISSION).id)
    assert view.status is CellStatus.FAILED and view.applied
    assert {p.path for p in view.problems} == {
        "envelope.size_y",
        "envelope.size_z",
        "envelope.mass",
    }


def test_provenance_only_changes_for_changed_fields() -> None:
    doc = doc_with_phase0()
    created = doc.changes()[0].id
    first = apply(doc, draft())
    mission = cell_of(doc.project, S.MISSION)
    view = read_artifact(doc.project, mission.id)
    assert view.provenance["envelope.mass"].source is FieldSource.ENTERED
    assert view.provenance["envelope.mass"].change_id == first
    # Untouched defaults keep their provenance.
    assert view.provenance["criteria.uncertainty_margin"].source is FieldSource.DEFAULT
    assert view.provenance["criteria.uncertainty_margin"].change_id == created
    assert "general.description" not in view.provenance  # empty fields have none

    second_draft = mission_of(view).model_copy(deep=True)
    second_draft.envelope.mass = 480.0
    second_draft.criteria.uncertainty_margin = 12.0
    second = apply(doc, second_draft)
    after = read_artifact(doc.project, mission.id)
    assert after.provenance["envelope.mass"].change_id == second
    assert after.provenance["criteria.uncertainty_margin"].source is FieldSource.ENTERED
    assert after.provenance["envelope.size_x"].change_id == first
    assert "2 campos cambiados" in doc.changes()[-1].summary


def test_same_content_is_not_a_change() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    revision = doc.revision
    with pytest.raises(NoChange):
        apply(doc, mission_of(read_artifact(doc.project, cell_of(doc.project, S.MISSION).id)))
    assert doc.revision == revision


def test_first_apply_of_defaults_is_recorded_without_outdating() -> None:
    doc = doc_with_phase0()
    environment = cell_of(doc.project, S.ENVIRONMENT)
    environment.status = CellStatus.UP_TO_DATE
    apply(doc, MissionArtifact())
    change = doc.changes()[-1]
    assert "sin cambios en los campos" in change.summary
    assert change.outdated_cell_ids == []
    assert cell_of(doc.project, S.MISSION).status is CellStatus.FAILED


def test_apply_outdates_downstream_only_when_content_changes() -> None:
    doc = doc_with_phase0()
    for cell in doc.project.cells:
        if cell.stage is not S.MISSION:
            cell.status = CellStatus.UP_TO_DATE
    mission_id = cell_of(doc.project, S.MISSION).id
    preview = read_artifact(doc.project, mission_id).outdates
    apply(doc, draft())
    outdated = {c.stage for c in doc.project.cells if c.status is CellStatus.OUTDATED}
    assert outdated == {S.ENVIRONMENT, S.GLOBAL_BALANCE, S.TCS_CONCEPT}
    assert preview == doc.changes()[-1].outdated_cell_ids
    assert read_artifact(doc.project, mission_id).outdates == []  # already outdated
    assert cell_of(doc.project, S.EQUIPMENT).status is CellStatus.UP_TO_DATE  # another root
    assert set(doc.changes()[-1].outdated_cell_ids) == {
        cell_of(doc.project, s).id for s in outdated
    }


def test_undo_and_redo() -> None:
    doc = doc_with_phase0()
    mission_id = cell_of(doc.project, S.MISSION).id
    apply(doc, draft())
    applied = doc.project.model_copy(deep=True)
    doc.undo(HUMAN)
    assert cell_of(doc.project, S.MISSION).status is CellStatus.NEVER_RUN
    assert mission_of(read_artifact(doc.project, mission_id)).envelope.mass is None
    doc.redo(HUMAN)
    assert doc.project == applied


# ---------------------------------------------------------------- copies and files


def test_duplicate_system_copies_the_artifact() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    doc.apply(
        Operation.DUPLICATE_SYSTEM,
        HUMAN,
        "",
        lambda p: duplicate_system(p, p.systems[0].id),
    )
    original, copied = [c for c in doc.project.cells if c.stage is S.MISSION]
    assert copied.form == original.form
    assert copied.status is CellStatus.UP_TO_DATE


def test_clipboard_copies_the_artifact() -> None:
    doc = doc_with_phase0()
    apply(doc, draft(envelope={"size_x": 1.0}))
    mission = cell_of(doc.project, S.MISSION)
    fragment = copy(doc.project, [], [mission.id])
    other = ProjectDocument.new("otro")
    change = other.apply(Operation.PASTE, HUMAN, "", lambda p: paste(p, fragment))
    pasted = cell_of(other.project, S.MISSION)
    assert pasted.form is not None and mission.form is not None
    assert pasted.form.artifact == mission.form.artifact
    assert pasted.status is CellStatus.FAILED  # applied in the source, revalidated
    provenance = pasted.form.provenance
    assert provenance["envelope.size_x"].source is FieldSource.ENTERED
    assert provenance["criteria.acceptance_margin"].source is FieldSource.DEFAULT
    assert all(p.change_id == change.id for p in provenance.values())


def test_version_1_fragments_paste_with_defaults() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    fragment = copy(doc.project, [doc.project.systems[0].id], [])
    fragment.schema_version = 1
    for system in fragment.systems:
        for cell in system.cells:
            cell.form = None
    paste(doc.project, fragment)
    pasted = [c for c in doc.project.cells if c.stage is S.MISSION][-1]
    assert pasted.status is CellStatus.NEVER_RUN
    assert pasted.form is not None and pasted.form.artifact == MissionArtifact().model_dump(
        mode="json"
    )


def test_save_and_open_roundtrip(tmp_path: Path) -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    path = tmp_path / "sat.hestia"
    write_project(path, doc.project, doc.history)
    project, history = read_project(path)
    assert project == doc.project
    assert [r.after for r in history] == [r.after for r in doc.history]
    mission = cell_of(project, S.MISSION)
    assert (
        read_artifact(project, mission.id).provenance
        == read_artifact(doc.project, mission.id).provenance
    )


def test_version_2_files_get_default_artifacts(tmp_path: Path) -> None:
    doc = doc_with_phase0()
    path = tmp_path / "v2.hestia"
    write_project(path, doc.project, [])
    conn = sqlite3.connect(path)
    conn.execute("ALTER TABLE cells DROP COLUMN form")
    conn.execute("PRAGMA user_version = 2")
    conn.commit()
    conn.close()
    loaded = read_project_file(path)
    mission = cell_of(loaded.project, S.MISSION)
    assert loaded.warnings == []
    assert mission.status is CellStatus.NEVER_RUN
    assert mission.form is not None
    assert all(p.change_id is None for p in mission.form.provenance.values())
    assert cell_of(loaded.project, S.EQUIPMENT).form is None
    # Environment parameters (ADR 0021) get their defaults too.
    environment = cell_of(loaded.project, S.ENVIRONMENT)
    assert environment.form is not None and environment.status is CellStatus.NEVER_RUN


# ---------------------------------------------------------------- ids of list items (ADR 0025)

NESTED_PREFIXES = {"items": "item", "items[].modes": "imode"}


def test_assign_ids_keeps_known_and_valid_proposed_ids_in_nested_lists() -> None:
    old: dict[str, Any] = {"items": [{"id": "item_old", "modes": [{"id": "imode_old"}]}]}
    data: dict[str, Any] = {
        "items": [
            {"id": "item_old", "modes": [{"id": "imode_old"}, {"id": "imode_beef"}]},
            {"id": "item_cafe", "modes": [{"id": None}, {"id": "imode_beef"}]},
            {"modes": [{"id": "item_abc"}]},
        ]
    }
    assign_ids(data, old, NESTED_PREFIXES)
    first, second, third = data["items"]
    assert first["id"] == "item_old"  # known, even without the hex format
    assert [m["id"] for m in first["modes"]] == ["imode_old", "imode_beef"]
    assert second["id"] == "item_cafe"  # proposed by the client
    generated = [second["modes"][0]["id"], second["modes"][1]["id"], third["modes"][0]["id"]]
    # Missing, repeated in the artifact (even under another item) or of another list: replaced.
    assert all(i.startswith("imode_") for i in generated)
    assert len({*generated, "imode_old", "imode_beef"}) == 5
    assert third["id"].startswith("item_")


def test_assign_ids_skips_lists_that_are_absent() -> None:
    data: dict[str, Any] = {"items": [{"name": "sin modos"}]}
    assign_ids(data, {}, NESTED_PREFIXES)
    assert data["items"][0]["id"].startswith("item_")
    assert "modes" not in data["items"][0]
