"""Operations on the artifacts of form stages (ADR 0017) and on the parameters of computation
stages (ADR 0021): read, dry validation and apply.

The draft lives in the client (UI or agent). Validating a draft changes nothing. Applying
replaces the cell's artifact in a single change of the history, updates the provenance of the
fields that changed and marks everything downstream as outdated if the content changed. For a
computation stage, applying different parameters also outdates the cell itself (if it has a
result) and never sets its status from the problems: that is what updating does.
"""

from typing import Any

from pydantic import BaseModel, ValidationError

from hestia_core.environment.parameters import EnvironmentParameters
from hestia_core.forms import Problem
from hestia_core.mission import MissionArtifact
from hestia_project.base import Schema
from hestia_project.catalog import StageType
from hestia_project.errors import InvalidOperationError
from hestia_project.forms import (
    FORMS,
    PENDING_CHANGE,
    FormContext,
    FormSpec,
    form_spec,
    is_form_stage,
    leaves,
    new_form_state,
    status_for,
)
from hestia_project.model import Cell, CellStatus, FieldProvenance, FieldSource, FormState, Project
from hestia_project.schematic import (
    CellContext,
    Outcome,
    cell_context,
    context_cells,
    get_cell,
    invalidate,
    new_id,
    would_invalidate,
)

Artifact = MissionArtifact | EnvironmentParameters
"""Artifact of a form stage or parameters of a computation stage. Both models forbid unknown
fields, so a JSON body resolves to the right one; the backend then validates it against the
model of the cell's stage."""


class NoChange(Exception):  # noqa: N818 - a signal, not an error
    """The operation would not change the project: nothing is recorded."""


class CellArtifact(Schema):
    """The artifact of a form cell (or the parameters of a computation cell) as applied, with
    everything needed to edit it."""

    cell_id: str
    stage: StageType
    status: CellStatus
    applied: bool
    """False until the first apply: the artifact holds the defaults."""
    artifact: Artifact
    problems: list[Problem]
    """Validation of the applied artifact. The parameters of a computation stage are validated
    against the current context (e.g. the orbit type of the mission)."""
    provenance: dict[str, FieldProvenance]
    """By leaf field path. Author, date and justification come from the change in the history."""
    context: CellContext
    outdates: list[str]
    """Cells that applying a changed artifact would mark as outdated (downstream cells with
    results and, for a computation stage, the cell itself), in project order. Preview for the
    confirmation; applying the same content or the first apply of the defaults outdates
    nothing."""


class ValidationResult(Schema):
    problems: list[Problem]
    """Empty: the draft is valid."""


def _form_cell(project: Project, cell_id: str) -> tuple[Cell, FormSpec, FormState]:
    cell = get_cell(project, cell_id)
    spec = form_spec(cell.stage)
    state = cell.form or new_form_state(cell.stage, change_id=None)
    assert state is not None
    return cell, spec, state


def _coerce(spec: FormSpec, draft: BaseModel | dict[str, Any]) -> BaseModel:
    data = draft.model_dump(mode="json") if isinstance(draft, BaseModel) else draft
    try:
        return spec.model.model_validate(data)
    except ValidationError as exc:
        raise InvalidOperationError(
            "El borrador no corresponde al artefacto de esta etapa.", errors=str(exc)
        ) from exc


def form_context(project: Project, cell_id: str) -> FormContext:
    """Artifacts of the form stages in the cell's context (the first provider of each type)."""
    result: dict[StageType, BaseModel] = {}
    for stage, cell_ids in context_cells(project, cell_id).items():
        spec = FORMS.get(stage)
        provider = get_cell(project, cell_ids[0])
        if spec is None or not is_form_stage(stage) or provider.form is None:
            continue
        result[stage] = spec.model.model_validate(provider.form.artifact)
    return result


def is_applied(cell: Cell, state: FormState) -> bool:
    """Whether the artifact (or the parameters) was applied at least once."""
    if is_form_stage(cell.stage):
        return cell.status is not CellStatus.NEVER_RUN
    return state.applied_change_id is not None


def artifact_problems(project: Project, cell: Cell) -> list[Problem]:
    """Problems of the applied artifact: as stored for form stages, revalidated against the
    current context for the parameters of a computation stage."""
    _, spec, state = _form_cell(project, cell.id)
    if is_form_stage(cell.stage):
        return state.problems
    return spec.validate(spec.model.model_validate(state.artifact), form_context(project, cell.id))


def read_artifact(project: Project, cell_id: str) -> CellArtifact:
    cell, spec, state = _form_cell(project, cell_id)
    artifact = spec.model.model_validate(state.artifact)
    assert isinstance(artifact, MissionArtifact | EnvironmentParameters)
    return CellArtifact(
        cell_id=cell.id,
        stage=cell.stage,
        status=cell.status,
        applied=is_applied(cell, state),
        artifact=artifact,
        problems=artifact_problems(project, cell),
        provenance=state.provenance,
        context=cell_context(project, cell.id),
        outdates=would_invalidate(project, [cell.id]),
    )


def validate_draft(project: Project, cell_id: str, draft: BaseModel) -> list[Problem]:
    """Problems of a draft for the cell's stage. Does not change the project."""
    cell, spec, _ = _form_cell(project, cell_id)
    return spec.validate(_coerce(spec, draft), form_context(project, cell.id))


def apply_artifact(project: Project, cell_id: str, draft: BaseModel) -> Outcome:
    """Replace the cell's artifact with ``draft``.

    Problems are allowed: a form cell is then failed; a computation cell keeps its status
    (updating it fails while its parameters have problems). Items of id'd lists keep the ids
    they had; new, unknown or repeated ids are replaced with backend ids. Raises ``NoChange``
    if the content is the same and the cell was applied before.
    """
    cell, spec, state = _form_cell(project, cell_id)
    data = _coerce(spec, draft).model_dump(mode="json")
    for path, prefix in spec.id_prefixes.items():
        _assign_ids(data, state.artifact, path, prefix)
    content_changed = data != state.artifact
    first_apply = not is_applied(cell, state)
    if not content_changed and not first_apply:
        raise NoChange

    problems = spec.validate(spec.model.model_validate(data), form_context(project, cell.id))
    provenance, changed = _provenance(state, data)
    cell.form = FormState(
        artifact=data, problems=problems, provenance=provenance, applied_change_id=PENDING_CHANGE
    )
    if is_form_stage(cell.stage):
        cell.status = status_for(problems)
    outdated = invalidate(project, [cell.id]) if content_changed else []

    if not content_changed:
        detail = "sin cambios en los campos"
    elif changed == 1:
        detail = "1 campo cambiado"
    else:
        detail = f"{changed} campos cambiados"
    state_text = "con problemas" if problems else "válido"
    return Outcome(
        summary=f"Aplicó «{cell.name}» ({detail}; {state_text}).",
        outdated_cell_ids=outdated,
    )


def _assign_ids(data: dict[str, Any], old: dict[str, Any], path: str, prefix: str) -> None:
    items: list[dict[str, Any]] = data.get(path) or []
    old_items: list[dict[str, Any]] = old.get(path) or []
    known: set[str] = {str(item["id"]) for item in old_items if item.get("id")}
    used: set[str] = set()
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in known or item_id in used:
            item_id = new_id(prefix)
            item["id"] = item_id
        used.add(item_id)


def _provenance(state: FormState, data: dict[str, Any]) -> tuple[dict[str, FieldProvenance], int]:
    """Provenance after applying ``data`` and the number of leaf fields that changed.

    Only changed fields get new provenance (``entered``, set by this change); unchanged fields
    keep theirs. Empty fields have none.
    """
    old = {leaf.key: leaf for leaf in leaves(state.artifact)}
    new_keys: set[str] = set()
    result: dict[str, FieldProvenance] = {}
    changed = 0
    for leaf in leaves(data):
        new_keys.add(leaf.key)
        previous = old.get(leaf.key)
        before = previous.value if previous is not None else None
        empty = leaf.value is None or leaf.value == []
        if before == leaf.value or (previous is None and empty):
            if previous is not None and previous.path in state.provenance and not empty:
                result[leaf.path] = state.provenance[previous.path]
            continue
        changed += 1
        if not empty:
            result[leaf.path] = FieldProvenance(
                source=FieldSource.ENTERED, change_id=PENDING_CHANGE
            )
    removed = [k for k, leaf in old.items() if k not in new_keys and leaf.value not in (None, [])]
    return result, changed + len(removed)
