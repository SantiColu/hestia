"""Artifacts of form stages (ADR 0017) and parameters of computation stages (ADR 0021). Each
endpoint only delegates to ``hestia_project.artifacts``."""

from fastapi import APIRouter

from hestia_api.deps import AuthorDep, WorkspaceDep
from hestia_api.errors import ERROR_RESPONSES
from hestia_api.schemas import ApplyArtifactRequest, ApplyArtifactResult, ArtifactDraft
from hestia_project import artifacts
from hestia_project.artifacts import CellArtifact, ValidationResult
from hestia_project.history import Operation

router = APIRouter(prefix="/project/cells", tags=["artifacts"], responses=ERROR_RESPONSES)


@router.get("/{cell_id}/artifact", operation_id="get_cell_artifact")
def get_cell_artifact(cell_id: str, workspace: WorkspaceDep) -> CellArtifact:
    """The applied artifact of a form cell (mission), or the applied parameters of a
    computation cell (environment), with its problems, per-field provenance, status and
    context. 422 `stage_not_implemented` for other stages."""
    return workspace.query(lambda p: artifacts.read_artifact(p, cell_id))


@router.post("/{cell_id}/artifact/validate", operation_id="validate_cell_artifact")
def validate_cell_artifact(
    cell_id: str, body: ArtifactDraft, workspace: WorkspaceDep
) -> ValidationResult:
    """Dry run: the problems of a draft. Changes nothing (no history, no status)."""
    return ValidationResult(
        problems=workspace.query(lambda p: artifacts.validate_draft(p, cell_id, body.artifact))
    )


@router.put("/{cell_id}/artifact", operation_id="apply_cell_artifact")
def apply_cell_artifact(
    cell_id: str, body: ApplyArtifactRequest, workspace: WorkspaceDep, author: AuthorDep
) -> ApplyArtifactResult:
    """Replace the cell's artifact with the draft in one change of the history (one undo).

    Requires a justification. Problems are allowed: a form cell is then failed (a computation
    cell fails when updated). Only the fields that changed get new provenance; everything
    downstream (and a computation cell itself) becomes outdated if the content changed.
    `change` is null if the content is the same as the applied one.
    """
    change, view = workspace.apply_if_changed(
        Operation.APPLY_ARTIFACT,
        author,
        body.justification,
        lambda p: artifacts.apply_artifact(p, cell_id, body.artifact),
    )
    cell = workspace.query(lambda p: artifacts.read_artifact(p, cell_id))
    return ApplyArtifactResult(change=change, view=view, cell=cell)
