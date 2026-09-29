"""Clipboard (ADR 0014). Each endpoint only delegates to ``hestia_project.clipboard``."""

from fastapi import APIRouter

from hestia_api.deps import AuthorDep, WorkspaceDep
from hestia_api.errors import ERROR_RESPONSES
from hestia_api.schemas import CopyRequest, PasteRequest
from hestia_project import clipboard
from hestia_project.clipboard import Fragment
from hestia_project.history import Operation
from hestia_project.workspace import MutationResult

router = APIRouter(prefix="/project/clipboard", tags=["clipboard"], responses=ERROR_RESPONSES)


@router.post("/copy", operation_id="copy_to_clipboard")
def copy_to_clipboard(body: CopyRequest, workspace: WorkspaceDep) -> Fragment:
    """Snapshot systems and cells as a versioned fragment. Changes nothing in the project."""
    return workspace.query(lambda p: clipboard.copy(p, body.system_ids, body.cell_ids))


@router.post("/paste", operation_id="paste_from_clipboard")
def paste_from_clipboard(
    body: PasteRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Create a fragment's systems and cells with new ids and its internal links.

    One change in the history (one undo reverts it). Links to cells outside the fragment are
    not copied; pasted cells are never run.
    """
    return workspace.apply(
        Operation.PASTE,
        author,
        body.justification,
        lambda p: clipboard.paste(p, body.fragment, body.position, body.target_system_id),
    )
