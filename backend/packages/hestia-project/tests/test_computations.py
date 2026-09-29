"""Computation stages (ADR 0021): parameters, update, result storage, states and provenance.

A fake computation is registered for ``environment`` so these rules are tested apart from the
physics of any stage.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from hestia_core.forms import InputRejectedError, Problem, ProblemCode
from hestia_core.mission import MissionArtifact
from hestia_project.artifacts import NoChange, apply_artifact, validate_draft
from hestia_project.catalog import StageType, TemplateId
from hestia_project.clipboard import copy, paste
from hestia_project.computations import COMPUTATIONS, ComputationSpec, read_result, update_cell
from hestia_project.document import ProjectDocument
from hestia_project.errors import StageNotImplementedError
from hestia_project.forms import FORMS, FormContext, FormSpec
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import Cell, CellStatus, Project
from hestia_project.schematic import Blueprint, create_system, link
from hestia_project.storage import read_project_file, write_project

S = StageType
HUMAN = Author(kind=ActorKind.HUMAN, name="ana")
AGENT = Author(kind=ActorKind.AGENT, name="stefan")

VALID: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 157_788_000.0},
    "orbit": {"type": "sso", "altitude": 600e3, "ltan": "10:30"},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
    "attitude_modes": [
        {
            "name": "Apuntado nadir",
            "primary_axis": "+Z",
            "primary_target": "nadir",
            "secondary_axis": "+X",
            "secondary_target": "velocity",
        }
    ],
}


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


def apply(doc: ProjectDocument, artifact: MissionArtifact) -> str:
    mission = cell_of(doc.project, S.MISSION)
    return doc.apply(
        Operation.APPLY_ARTIFACT, AGENT, "datos", lambda p: apply_artifact(p, mission.id, artifact)
    ).id


class FakeParameters(BaseModel):
    schema_version: int = 1
    factor: float | None = 2.0


class FakeResult(BaseModel):
    value: float


def _validate(parameters: FakeParameters, context: FormContext) -> list[Problem]:
    problems: list[Problem] = []
    if parameters.factor is None or parameters.factor <= 0:
        problems.append(Problem(path="factor", code=ProblemCode.MIN, message="Factor > 0."))
    mission = context.get(S.MISSION)
    if isinstance(mission, MissionArtifact) and parameters.factor == 7:
        problems.append(Problem(path="factor", code=ProblemCode.NOT_ALLOWED, message="Con misión."))
    return problems


def _run(parameters: BaseModel, context: FormContext) -> BaseModel:
    assert isinstance(parameters, FakeParameters) and parameters.factor is not None
    mission = context[S.MISSION]
    assert isinstance(mission, MissionArtifact) and mission.envelope.mass is not None
    if parameters.factor == 13:
        raise InputRejectedError(
            [Problem(path="orbit", code=ProblemCode.ECCENTRICITY_OUT_OF_RANGE, message="No.")]
        )
    return FakeResult(value=mission.envelope.mass * parameters.factor)


@pytest.fixture(autouse=True)
def fake_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setitem(
        FORMS,
        S.ENVIRONMENT,
        FormSpec(model=FakeParameters, defaults=FakeParameters, validate=_validate),
    )
    monkeypatch.setitem(
        COMPUTATIONS,
        S.ENVIRONMENT,
        ComputationSpec(
            result_model=FakeResult,
            run=_run,
            provider="fake",
            provider_version="1",
            code_version="0.1.0",
        ),
    )
    yield


def update(doc: ProjectDocument, stage: StageType = S.ENVIRONMENT) -> str:
    cell = cell_of(doc.project, stage)
    return doc.apply(
        Operation.UPDATE_CELL, AGENT, "", lambda p: update_cell(p, doc.results, cell.id)
    ).id


def set_factor(doc: ProjectDocument, factor: float) -> str:
    env = cell_of(doc.project, S.ENVIRONMENT)
    return doc.apply(
        Operation.APPLY_ARTIFACT,
        HUMAN,
        "otro factor",
        lambda p: apply_artifact(p, env.id, FakeParameters(factor=factor)),
    ).id


def result_value(doc: ProjectDocument) -> float:
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.result_id is not None
    return FakeResult.model_validate(doc.results[env.result_id].data).value


# ---------------------------------------------------------------- update


def test_new_cell_has_default_parameters_and_never_ran() -> None:
    doc = doc_with_phase0()
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.NEVER_RUN
    assert env.form is not None and env.form.artifact == {"schema_version": 1, "factor": 2.0}
    assert env.form.applied_change_id is None and env.result_id is None


def test_update_without_mission_in_context_fails_with_missing() -> None:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(stage=S.ENVIRONMENT)),
    )
    change_id = update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.FAILED and env.result_id is None
    assert [(p.path, p.code) for p in env.problems] == [("context", ProblemCode.MISSING)]
    change = doc.changes()[-1]
    assert change.id == change_id and change.operation is Operation.UPDATE_CELL
    assert change.author == AGENT and change.justification == ""
    assert doc.state().undo_label == "actualizar"


def test_update_with_an_unapplied_or_invalid_mission_fails() -> None:
    doc = doc_with_phase0()
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert [p.code for p in env.problems] == [ProblemCode.CONTEXT_INVALID]
    assert "no está aplicada" in env.problems[0].message
    # Failing again the same way records nothing.
    with pytest.raises(NoChange):
        update(doc)
    apply(doc, draft(envelope={"size_x": 1.0}))
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.FAILED
    assert "tiene problemas" in env.problems[0].message


def test_update_stores_the_result_outside_the_snapshots() -> None:
    doc = doc_with_phase0()
    applied = apply(doc, draft())
    change_id = update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.UP_TO_DATE and env.problems == []
    assert env.result_id is not None and env.result_id in doc.results
    assert result_value(doc) == 450.0 * 2.0
    stored = doc.results[env.result_id]
    assert stored.parameters == {"schema_version": 1, "factor": 2.0}
    # The history snapshot references the result by id; it does not copy it.
    after = cell_of(doc.history[-1].after, S.ENVIRONMENT)
    assert after.result_id == env.result_id
    assert "value" not in doc.history[-1].after.model_dump_json()

    provenance = env.provenance
    assert provenance is not None
    assert provenance.change_id == change_id
    assert provenance.provider == "fake" and provenance.provider_version == "1"
    assert provenance.parameters_change_id is None  # defaults, never applied
    mission = cell_of(doc.project, S.MISSION)
    assert [(s.stage, s.cell_id, s.change_id) for s in provenance.context] == [
        (S.MISSION, mission.id, applied)
    ]


def test_updating_an_up_to_date_cell_changes_nothing() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    update(doc)
    revision = doc.revision
    with pytest.raises(NoChange):
        update(doc)
    assert doc.revision == revision


def test_updating_outdates_downstream() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    balance = cell_of(doc.project, S.GLOBAL_BALANCE)
    balance.status = CellStatus.UP_TO_DATE
    update(doc)
    assert cell_of(doc.project, S.GLOBAL_BALANCE).status is CellStatus.OUTDATED
    assert doc.changes()[-1].outdated_cell_ids == [balance.id]  # the concept never ran


def test_upstream_change_outdates_without_recomputing() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    update(doc)
    first = cell_of(doc.project, S.ENVIRONMENT).result_id
    apply(doc, draft(envelope={**VALID["envelope"], "mass": 500.0}))
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.OUTDATED
    assert env.result_id == first and result_value(doc) == 900.0  # kept, not recomputed
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.UP_TO_DATE and env.result_id != first
    assert result_value(doc) == 1000.0


def test_applying_parameters_outdates_the_cell_itself() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    # Never run: applying parameters keeps it never run.
    first = set_factor(doc, 3.0)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.NEVER_RUN
    assert env.form is not None and env.form.applied_change_id == first
    update(doc)
    provenance = cell_of(doc.project, S.ENVIRONMENT).provenance
    assert provenance is not None and provenance.parameters_change_id == first
    set_factor(doc, 4.0)
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.OUTDATED
    assert doc.changes()[-1].outdated_cell_ids == [env_id]
    update(doc)
    assert result_value(doc) == 1800.0


def test_parameters_are_validated_against_the_context() -> None:
    doc = doc_with_phase0()
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert validate_draft(doc.project, env.id, FakeParameters(factor=7)) != []
    set_factor(doc, 7)  # problems are allowed when applying
    apply(doc, draft())
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.FAILED
    assert [(p.path, p.code) for p in env.problems] == [("factor", ProblemCode.NOT_ALLOWED)]


def test_rejected_inputs_fail_and_keep_the_previous_result() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    update(doc)
    first = cell_of(doc.project, S.ENVIRONMENT).result_id
    set_factor(doc, 13)
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.FAILED and env.result_id == first
    assert [p.code for p in env.problems] == [ProblemCode.ECCENTRICITY_OUT_OF_RANGE]
    cell_result = read_result(doc.project, doc.results, env.id)
    assert cell_result.problems == env.problems and cell_result.result_id == first
    assert cell_result.environment is None  # a fake result, not an environment


def test_undo_returns_to_the_previous_result() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    update(doc)
    first = cell_of(doc.project, S.ENVIRONMENT).result_id
    set_factor(doc, 5.0)
    update(doc)
    doc.undo(HUMAN)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.OUTDATED and env.result_id == first
    doc.redo(HUMAN)
    assert result_value(doc) == 2250.0


def test_form_stages_cannot_be_updated() -> None:
    doc = doc_with_phase0()
    with pytest.raises(StageNotImplementedError):
        update(doc, S.MISSION)


def test_linking_a_mission_later() -> None:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM, HUMAN, "", lambda p: create_system(p, Blueprint(stage=S.MISSION))
    )
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(stage=S.ENVIRONMENT)),
    )
    apply(doc, draft())
    update(doc)
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.FAILED
    mission, env = cell_of(doc.project, S.MISSION), cell_of(doc.project, S.ENVIRONMENT)
    doc.apply(Operation.LINK, HUMAN, "", lambda p: link(p, mission.id, env.id))
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.OUTDATED
    update(doc)
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.UP_TO_DATE


# ---------------------------------------------------------------- copies and files


def test_clipboard_copies_parameters_but_not_results() -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    set_factor(doc, 3.0)
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    fragment = copy(doc.project, [], [env.id])
    other = ProjectDocument.new("otro")
    other.apply(Operation.PASTE, HUMAN, "", lambda p: paste(p, fragment))
    pasted = cell_of(other.project, S.ENVIRONMENT)
    assert pasted.status is CellStatus.NEVER_RUN and pasted.result_id is None
    assert pasted.form is not None and pasted.form.artifact["factor"] == 3.0
    assert pasted.form.applied_change_id == other.changes()[-1].id


def test_results_survive_save_and_open(tmp_path: Path) -> None:
    doc = doc_with_phase0()
    apply(doc, draft())
    update(doc)
    set_factor(doc, 3.0)
    update(doc)
    orphan = doc.results[cell_of(doc.project, S.ENVIRONMENT).result_id or ""].model_copy(
        update={"id": "result_orphan"}
    )
    doc.results[orphan.id] = orphan
    path = tmp_path / "sat.hestia"
    write_project(path, doc.project, doc.history, doc.results)
    loaded = read_project_file(path)
    assert loaded.project == doc.project
    # Both results are referenced (the first by the history); the orphan is dropped.
    assert set(loaded.results) == set(doc.results) - {"result_orphan"}
    assert len(loaded.results) == 2
    reopened = ProjectDocument(loaded.project, path, loaded.history, loaded.results)
    assert result_value(reopened) == 1350.0
    # The first result stays readable from the history (audit of an old result).
    first_update = next(r for r in loaded.history if r.change.operation is Operation.UPDATE_CELL)
    first_id = cell_of(first_update.after, S.ENVIRONMENT).result_id or ""
    assert FakeResult.model_validate(loaded.results[first_id].data).value == 900.0


def test_version_3_files_recover_applied_changes(tmp_path: Path) -> None:
    doc = doc_with_phase0()
    applied = apply(doc, draft())
    path = tmp_path / "v3.hestia"
    project = doc.project.model_copy(deep=True)
    for cell in project.cells:
        if cell.form is not None:
            cell.form.applied_change_id = None
    write_project(path, project, doc.history)
    conn = sqlite3.connect(path)
    conn.execute("ALTER TABLE cells DROP COLUMN result_id")
    conn.execute("ALTER TABLE cells DROP COLUMN problems")
    conn.execute("DROP TABLE results")
    conn.execute("PRAGMA user_version = 3")
    conn.commit()
    conn.close()
    loaded = read_project_file(path)
    mission = cell_of(loaded.project, S.MISSION)
    assert mission.form is not None and mission.form.applied_change_id == applied
    env = cell_of(loaded.project, S.ENVIRONMENT)
    assert env.status is CellStatus.NEVER_RUN and env.form is not None
    assert loaded.results == {}
