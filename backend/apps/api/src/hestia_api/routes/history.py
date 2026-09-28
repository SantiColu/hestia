from fastapi import APIRouter

from hestia_api.deps import AuthorDep, WorkspaceDep
from hestia_api.errors import ERROR_RESPONSES
from hestia_api.schemas import WriteRequest
from hestia_project.history import Change
from hestia_project.workspace import MutationResult

router = APIRouter(prefix="/project", tags=["history"], responses=ERROR_RESPONSES)


@router.get("/history", operation_id="get_history")
def get_history(workspace: WorkspaceDep) -> list[Change]:
    """Every change of the project, oldest first, with author and justification."""
    return workspace.history()


@router.post("/undo", operation_id="undo")
def undo(body: WriteRequest, workspace: WorkspaceDep, author: AuthorDep) -> MutationResult:
    """Undo the last change of this session (recorded in the history as well)."""
    return workspace.undo(author, body.justification)


@router.post("/redo", operation_id="redo")
def redo(body: WriteRequest, workspace: WorkspaceDep, author: AuthorDep) -> MutationResult:
    """Redo the last undone change."""
    return workspace.redo(author, body.justification)
