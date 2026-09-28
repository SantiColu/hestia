"""Hestia MCP server.

Every tool maps to exactly one Hestia REST API operation (see ``api.OPERATIONS``). This module
talks HTTP only; it must never import backend packages. Write tools require a
``justification``, stored in the project history with the agent as author.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from hestia_mcp import __version__
from hestia_mcp.api import call

server = MCPServer(
    name="hestia",
    version=__version__,
    instructions=(
        "Hestia: preliminary thermal control system design for medium satellites. "
        "A project is a schematic of systems (groups of cells), cells (instances of a workflow "
        "stage) and links (a cell's output feeding another cell's input). Start with "
        "get_session and get_catalog. Every write needs a justification. "
        "All numbers come from the Hestia API; never compute physical results yourself."
    ),
)

TOOL_OPERATIONS: dict[str, str] = {}
"""Tool name → API operationId."""

StageType = Literal[
    "mission",
    "environment",
    "global_balance",
    "tcs_concept",
    "discretization",
    "couplings",
    "load_cases",
    "solution",
    "margins",
    "sensitivity",
]
TemplateId = Literal["phase_0", "phase_1"]
Json = dict[str, Any]


def _tool[F: Callable[..., Awaitable[Any]]](operation_id: str) -> Callable[[F], F]:
    """Register ``fn`` as an MCP tool that maps to the API operation ``operation_id``."""

    def register(fn: F) -> F:
        TOOL_OPERATIONS[fn.__name__] = operation_id
        return server.tool()(fn)

    return register


def _position(x: float | None, y: float | None) -> Json | None:
    return {"x": x, "y": y} if x is not None and y is not None else None


def _blueprint(template: TemplateId | None, stage: StageType | None) -> Json:
    return {"template": template, "stage": stage}


# ---------------------------------------------------------------- system & catalog


@_tool("health")
async def ping() -> Json:
    """Check that the Hestia API is reachable. Maps to GET /health."""
    return await call("health")


@_tool("get_catalog")
async def get_catalog() -> Json:
    """Stage types (with the stage types each one accepts as input), phases and templates."""
    return await call("get_catalog")


# ---------------------------------------------------------------- files


@_tool("get_session")
async def get_session() -> Json:
    """The open project (systems, cells, links, file state) or null if none is open."""
    return await call("get_session")


@_tool("list_recent_projects")
async def list_recent_projects() -> list[Json]:
    """Recently opened .hestia files; `exists` is false for moved or deleted files."""
    return await call("list_recent_projects")


@_tool("remove_recent_project")
async def remove_recent_project(path: str) -> list[Json]:
    """Remove an entry from the recent projects list (the file is not touched)."""
    return await call("remove_recent_project", json={"path": path})


@_tool("new_project")
async def new_project(name: str | None = None, discard_unsaved: bool = False) -> Json:
    """Start an empty, unsaved project. Fails if the open one has unsaved changes."""
    return await call("new_project", json={"name": name, "discard_unsaved": discard_unsaved})


@_tool("open_project")
async def open_project(path: str, force: bool = False, discard_unsaved: bool = False) -> Json:
    """Open a .hestia file. Fails with project_locked if another Hestia instance has it open;
    `force` takes the file over (only if the user confirms the other instance is gone)."""
    return await call(
        "open_project",
        json={"path": path, "force": force, "discard_unsaved": discard_unsaved},
    )


@_tool("save_project")
async def save_project() -> Json:
    """Save the open project to its file. Fails with no_path if it was never saved."""
    return await call("save_project")


@_tool("save_project_as")
async def save_project_as(path: str) -> Json:
    """Save the open project to a new .hestia file and keep working on it."""
    return await call("save_project_as", json={"path": path})


@_tool("close_project")
async def close_project(discard_unsaved: bool = False) -> Json:
    """Close the open project. Fails if it has unsaved changes, unless discarding them."""
    return await call("close_project", json={"discard_unsaved": discard_unsaved})


# ---------------------------------------------------------------- history


@_tool("get_history")
async def get_history() -> list[Json]:
    """Every change of the project with author, justification and summary, oldest first."""
    return await call("get_history")


@_tool("undo")
async def undo(justification: str) -> Json:
    """Undo the last change made in this session (by anyone)."""
    return await call("undo", json={"justification": justification})


@_tool("redo")
async def redo(justification: str) -> Json:
    """Redo the last undone change."""
    return await call("redo", json={"justification": justification})


# ---------------------------------------------------------------- schematic


@_tool("create_system")
async def create_system(
    justification: str,
    template: TemplateId | None = None,
    stage: StageType | None = None,
    name: str | None = None,
    x: float | None = None,
    y: float | None = None,
) -> Json:
    """Create a system: a whole phase from `template` (cells already linked) or a single cell
    of type `stage`. Pass exactly one of them. Position (x, y) is optional."""
    return await call(
        "create_system",
        json={
            **_blueprint(template, stage),
            "name": name,
            "position": _position(x, y),
            "justification": justification,
        },
    )


@_tool("rename_system")
async def rename_system(system_id: str, name: str, justification: str) -> Json:
    """Rename a system."""
    return await call(
        "rename_system",
        path={"system_id": system_id},
        json={"name": name, "justification": justification},
    )


@_tool("move_system")
async def move_system(system_id: str, x: float, y: float, justification: str) -> Json:
    """Move a system on the schematic canvas."""
    return await call(
        "move_system",
        path={"system_id": system_id},
        json={"position": {"x": x, "y": y}, "justification": justification},
    )


@_tool("duplicate_system")
async def duplicate_system(system_id: str, justification: str) -> Json:
    """Copy a system with its cells, internal links and incoming links."""
    return await call(
        "duplicate_system", path={"system_id": system_id}, json={"justification": justification}
    )


@_tool("delete_system")
async def delete_system(system_id: str, justification: str) -> Json:
    """Delete a system with its cells and links. Dependent cells become outdated."""
    return await call(
        "delete_system", path={"system_id": system_id}, json={"justification": justification}
    )


@_tool("add_cell")
async def add_cell(
    system_id: str, stage: StageType, justification: str, name: str | None = None
) -> Json:
    """Add a cell of type `stage` to a system; it is linked inside the system when unambiguous."""
    return await call(
        "add_cell",
        path={"system_id": system_id},
        json={"stage": stage, "name": name, "justification": justification},
    )


@_tool("rename_cell")
async def rename_cell(cell_id: str, name: str, justification: str) -> Json:
    """Rename a cell."""
    return await call(
        "rename_cell",
        path={"cell_id": cell_id},
        json={"name": name, "justification": justification},
    )


@_tool("delete_cell")
async def delete_cell(cell_id: str, justification: str) -> Json:
    """Delete a cell and its links (an emptied system is deleted too)."""
    return await call(
        "delete_cell", path={"cell_id": cell_id}, json={"justification": justification}
    )


@_tool("branch_cell")
async def branch_cell(
    cell_id: str,
    justification: str,
    template: TemplateId | None = None,
    stage: StageType | None = None,
    name: str | None = None,
) -> Json:
    """Branch: create a new system (a `template` or a single `stage`) fed by `cell_id`,
    e.g. a second environment from the same mission. Use list_branch_targets first."""
    return await call(
        "branch_cell",
        path={"cell_id": cell_id},
        json={**_blueprint(template, stage), "name": name, "justification": justification},
    )


@_tool("list_branch_targets")
async def list_branch_targets(
    template: TemplateId | None = None, stage: StageType | None = None
) -> Json:
    """Cells from which a template or stage (exactly one) can be branched."""
    params = {"template": template} if template else {"stage": stage or ""}
    return await call("list_branch_targets", params=params)


@_tool("list_link_targets")
async def list_link_targets(cell_id: str) -> Json:
    """Cells that `cell_id` could feed with a new link right now."""
    return await call("list_link_targets", path={"cell_id": cell_id})


@_tool("link_cells")
async def link_cells(source_cell_id: str, target_cell_id: str, justification: str) -> Json:
    """Feed the output of one cell into the matching input of another. The workflow decides
    which links are valid; each input has a single source."""
    return await call(
        "link_cells",
        json={
            "source_cell_id": source_cell_id,
            "target_cell_id": target_cell_id,
            "justification": justification,
        },
    )


@_tool("unlink_cells")
async def unlink_cells(link_id: str, justification: str) -> Json:
    """Remove a link. Its target and everything downstream become outdated."""
    return await call(
        "unlink_cells", path={"link_id": link_id}, json={"justification": justification}
    )


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
