"""Schematic operations. Each endpoint only delegates to ``hestia_project.schematic``."""

from typing import Annotated

from fastapi import APIRouter, Query

from hestia_api.deps import AuthorDep, WorkspaceDep
from hestia_api.errors import ERROR_RESPONSES
from hestia_api.schemas import (
    AddCellRequest,
    BranchRequest,
    CellIds,
    CreateSystemRequest,
    DuplicateSystemRequest,
    LinkRequest,
    MoveSystemRequest,
    RenameRequest,
    WriteRequest,
)
from hestia_project import schematic as ops
from hestia_project.catalog import StageType, TemplateId
from hestia_project.errors import InvalidOperationError
from hestia_project.history import Operation
from hestia_project.schematic import Blueprint, CellContext
from hestia_project.workspace import MutationResult

router = APIRouter(prefix="/project", tags=["schematic"], responses=ERROR_RESPONSES)


def _blueprint(body: Blueprint) -> Blueprint:
    return Blueprint(template=body.template, stage=body.stage)


@router.post("/systems", operation_id="create_system")
def create_system(
    body: CreateSystemRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Create a system from a phase template (cells already linked) or with one cell."""
    blueprint = _blueprint(body)
    return workspace.apply(
        Operation.CREATE_SYSTEM,
        author,
        body.justification,
        lambda p: ops.create_system(p, blueprint, body.name, body.position),
    )


@router.patch("/systems/{system_id}", operation_id="rename_system")
def rename_system(
    system_id: str, body: RenameRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    return workspace.apply(
        Operation.RENAME_SYSTEM,
        author,
        body.justification,
        lambda p: ops.rename_system(p, system_id, body.name),
    )


@router.post("/systems/{system_id}/move", operation_id="move_system")
def move_system(
    system_id: str, body: MoveSystemRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Move a system on the canvas."""
    return workspace.apply(
        Operation.MOVE_SYSTEM,
        author,
        body.justification,
        lambda p: ops.move_system(p, system_id, body.position),
    )


@router.post("/systems/{system_id}/duplicate", operation_id="duplicate_system")
def duplicate_system(
    system_id: str, body: DuplicateSystemRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Copy a system with its cells, internal links and incoming links."""
    return workspace.apply(
        Operation.DUPLICATE_SYSTEM,
        author,
        body.justification,
        lambda p: ops.duplicate_system(p, system_id, body.position),
    )


@router.delete("/systems/{system_id}", operation_id="delete_system")
def delete_system(
    system_id: str, body: WriteRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Delete a system, its cells and their links. Requires a justification."""
    return workspace.apply(
        Operation.DELETE_SYSTEM,
        author,
        body.justification,
        lambda p: ops.delete_system(p, system_id),
    )


@router.post("/systems/{system_id}/cells", operation_id="add_cell")
def add_cell(
    system_id: str, body: AddCellRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Add a cell to a system; it is linked to the cells of that system that complete its
    context (as target) or whose context it completes (as source)."""
    return workspace.apply(
        Operation.ADD_CELL,
        author,
        body.justification,
        lambda p: ops.add_cell(p, system_id, body.stage, body.name),
    )


@router.patch("/cells/{cell_id}", operation_id="rename_cell")
def rename_cell(
    cell_id: str, body: RenameRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    return workspace.apply(
        Operation.RENAME_CELL,
        author,
        body.justification,
        lambda p: ops.rename_cell(p, cell_id, body.name),
    )


@router.delete("/cells/{cell_id}", operation_id="delete_cell")
def delete_cell(
    cell_id: str, body: WriteRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Delete a cell and its links (an emptied system is deleted). Requires a justification."""
    return workspace.apply(
        Operation.DELETE_CELL,
        author,
        body.justification,
        lambda p: ops.delete_cell(p, cell_id),
    )


@router.post("/cells/{cell_id}/branch", operation_id="branch_cell")
def branch_cell(
    cell_id: str, body: BranchRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Create a new system (template or stage) and link this cell to its first cell that
    accepts it."""
    blueprint = _blueprint(body)
    return workspace.apply(
        Operation.BRANCH,
        author,
        body.justification,
        lambda p: ops.branch(p, cell_id, blueprint, body.name, body.position),
    )


@router.get("/cells/{cell_id}/link-targets", operation_id="list_link_targets")
def list_link_targets(cell_id: str, workspace: WorkspaceDep) -> CellIds:
    """Cells this cell could feed with a new link right now."""
    return CellIds(cell_ids=workspace.query(lambda p: ops.link_targets(p, cell_id)))


@router.get("/cells/{cell_id}/context", operation_id="get_cell_context")
def get_cell_context(cell_id: str, workspace: WorkspaceDep) -> CellContext:
    """Resolved context of a cell: the cell that provides each upstream stage type, and the
    required types that are missing (the cell cannot run until they are linked)."""
    return workspace.query(lambda p: ops.cell_context(p, cell_id))


@router.get("/cells/{cell_id}/branch-options", operation_id="list_branch_options")
def list_branch_options(cell_id: str, workspace: WorkspaceDep) -> list[Blueprint]:
    """Templates and stages that can be branched from this cell."""
    return workspace.query(lambda p: ops.branch_options(p, cell_id))


@router.get("/branch-targets", operation_id="list_branch_targets")
def list_branch_targets(
    workspace: WorkspaceDep,
    template: Annotated[TemplateId | None, Query()] = None,
    stage: Annotated[StageType | None, Query()] = None,
) -> CellIds:
    """Cells onto which a template or stage can be dropped to branch. Pass exactly one."""
    if (template is None) == (stage is None):
        raise InvalidOperationError("Indicá exactamente uno de «template» o «stage».")
    blueprint = Blueprint(template=template, stage=stage)
    return CellIds(cell_ids=workspace.query(lambda p: ops.branch_targets(p, blueprint)))


@router.post("/links", operation_id="link_cells")
def link_cells(body: LinkRequest, workspace: WorkspaceDep, author: AuthorDep) -> MutationResult:
    """Link two cells: the target gets the source's whole context (ADR 0016). A second parent
    is only valid if the contexts share no stage type (union)."""
    return workspace.apply(
        Operation.LINK,
        author,
        body.justification,
        lambda p: ops.link(p, body.source_cell_id, body.target_cell_id),
    )


@router.delete("/links/{link_id}", operation_id="unlink_cells")
def unlink_cells(
    link_id: str, body: WriteRequest, workspace: WorkspaceDep, author: AuthorDep
) -> MutationResult:
    """Remove a link; its target and everything downstream become outdated."""
    return workspace.apply(
        Operation.UNLINK,
        author,
        body.justification,
        lambda p: ops.unlink(p, link_id),
    )
