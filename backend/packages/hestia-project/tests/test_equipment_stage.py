"""The equipment stage in a project: defaults, apply with proposed ids, copies (ADR 0017, 0025)."""

from typing import Any

from hestia_core.equipment import EquipmentArtifact
from hestia_core.forms import ProblemCode
from hestia_project.artifacts import apply_artifact, read_artifact, validate_draft
from hestia_project.catalog import StageType, TemplateId
from hestia_project.clipboard import copy, paste
from hestia_project.document import ProjectDocument
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import Cell, CellStatus, FieldSource, Project
from hestia_project.schematic import Blueprint, create_system, duplicate_system

S = StageType
HUMAN = Author(kind=ActorKind.HUMAN, name="ana")

WHEEL: dict[str, Any] = {
    "id": "item_00a1",
    "name": "Rueda de reacción",
    "subsystem": "aocs",
    "quantity": 4,
    "mass": 0.9,
    "location": "internal",
    "modes": [
        {"id": "imode_00a1", "name": "Standby", "dissipation": 3.0},
        {"id": "imode_00a2", "name": "Pico", "dissipation": 20.0},
    ],
    "operating_min": 253.15,
    "operating_max": 333.15,
}
VALID: dict[str, Any] = {
    "items": [WHEEL],
    "operating_modes": [
        {"id": "opmode_00a1", "name": "Adquisición", "states": {"item_00a1": "imode_00a2"}}
    ],
}


def cell_of(project: Project, stage: StageType) -> Cell:
    return next(c for c in project.cells if c.stage is stage)


def phase0() -> ProjectDocument:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )
    return doc


def apply(doc: ProjectDocument, data: dict[str, Any]) -> None:
    cell_id = cell_of(doc.project, S.EQUIPMENT).id
    draft = EquipmentArtifact.model_validate(data)
    doc.apply(Operation.APPLY_ARTIFACT, HUMAN, "", lambda p: apply_artifact(p, cell_id, draft))


def equipment_of(doc: ProjectDocument) -> EquipmentArtifact:
    artifact = read_artifact(doc.project, cell_of(doc.project, S.EQUIPMENT).id).artifact
    assert isinstance(artifact, EquipmentArtifact)
    return artifact


def test_new_equipment_cell_has_the_defaults() -> None:
    doc = phase0()
    view = read_artifact(doc.project, cell_of(doc.project, S.EQUIPMENT).id)
    assert view.status is CellStatus.NEVER_RUN and not view.applied
    artifact = equipment_of(doc)
    assert [i.name for i in artifact.items] == ["Plataforma"]
    assert view.provenance["items[0].name"].source is FieldSource.DEFAULT
    assert view.provenance["operating_modes[0].states.item_1"].source is FieldSource.DEFAULT
    assert {p.path for p in view.problems} >= {"items[0].mass", "items[0].modes[0].dissipation"}


def test_apply_keeps_proposed_ids_and_generates_the_missing_ones() -> None:
    doc = phase0()
    new_mode = {"name": "Nominal", "dissipation": 8.0}
    apply(doc, VALID | {"items": [WHEEL | {"modes": [*WHEEL["modes"], new_mode]}]})
    artifact = equipment_of(doc)
    [item] = artifact.items
    assert item.id == "item_00a1"
    assert [m.id for m in item.modes][:2] == ["imode_00a1", "imode_00a2"]
    generated = item.modes[2].id
    assert generated is not None and generated.startswith("imode_")
    assert artifact.operating_modes[0].id == "opmode_00a1"
    assert cell_of(doc.project, S.EQUIPMENT).status is CellStatus.UP_TO_DATE
    assert len(doc.changes()) == 2  # create + one apply


def test_apply_with_problems_leaves_the_cell_failed() -> None:
    doc = phase0()
    apply(doc, VALID | {"items": [WHEEL | {"quantity": 0}]})
    view = read_artifact(doc.project, cell_of(doc.project, S.EQUIPMENT).id)
    assert view.status is CellStatus.FAILED
    assert [(p.path, p.code) for p in view.problems] == [("items[0].quantity", ProblemCode.MIN)]


def test_dry_validation_reports_problems_by_path() -> None:
    doc = phase0()
    cell_id = cell_of(doc.project, S.EQUIPMENT).id
    modes = [{"name": "Standby", "dissipation": -1.0}]
    draft = EquipmentArtifact.model_validate(VALID | {"items": [WHEEL | {"modes": modes}]})
    result = validate_draft(doc.project, cell_id, draft)
    assert ("items[0].modes[0].dissipation", ProblemCode.MIN) in {
        (p.path, p.code) for p in result.problems
    }
    assert doc.revision == 1


def test_apply_outdates_downstream() -> None:
    doc = phase0()
    for cell in doc.project.cells:
        if cell.stage is not S.EQUIPMENT:
            cell.status = CellStatus.UP_TO_DATE
    apply(doc, VALID)
    outdated = {c.stage for c in doc.project.cells if c.status is CellStatus.OUTDATED}
    assert outdated == {S.GLOBAL_BALANCE, S.TCS_CONCEPT}


def test_duplicate_and_paste_keep_the_artifact() -> None:
    doc = phase0()
    apply(doc, VALID)
    original = cell_of(doc.project, S.EQUIPMENT)
    doc.apply(Operation.DUPLICATE_SYSTEM, HUMAN, "", lambda p: duplicate_system(p, p.systems[0].id))
    copied = [c for c in doc.project.cells if c.stage is S.EQUIPMENT][-1]
    assert copied.form == original.form and copied.status is CellStatus.UP_TO_DATE

    fragment = copy(doc.project, [], [original.id])
    other = ProjectDocument.new("otro")
    other.apply(Operation.PASTE, HUMAN, "", lambda p: paste(p, fragment))
    pasted = cell_of(other.project, S.EQUIPMENT)
    assert pasted.form is not None and original.form is not None
    assert pasted.form.artifact == original.form.artifact
    assert pasted.status is CellStatus.UP_TO_DATE
