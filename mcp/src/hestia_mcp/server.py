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
        "stage) and links. A link passes the source cell and everything upstream of it (its "
        "context) to the target; each stage type requires some types in its context "
        "(get_cell_context shows what is missing). Form stages (mission) are edited with "
        "apply_cell_artifact; computation stages (environment) take parameters the same way "
        "and run with update_cell, then get_cell_result. Start with get_session and get_catalog. "
        "Every write needs a justification (updating a computation cell accepts an empty one). "
        "All numbers come from the Hestia API; never compute physical results yourself."
    ),
)

TOOL_OPERATIONS: dict[str, str] = {}
"""Tool name → API operationId."""

StageType = Literal[
    "mission",
    "environment",
    "equipment",
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
    """Stage types in catalog order (class: root, form or computation; the stage types each one
    requires in its context; whether it is implemented), phases and templates."""
    return await call("get_catalog")


@_tool("get_artifact_schema")
async def get_artifact_schema(stage: StageType) -> Json:
    """JSON Schema of the artifact of a form stage (`mission`) or of the parameters of a
    computation stage (`environment`): fields, enums, SI unit (`x-unit`) of each physical field,
    library defaults (`x-default`, `x-default-source`) and which fields apply to each orbit type
    (`x-show-if`). Values are always in SI units and kelvin."""
    return await call("get_artifact_schema", path={"stage": stage})


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
    """Add a cell of type `stage` to a system. It is linked to the cells of the system that
    complete its context, and to those whose context it completes."""
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
    """Branch: create a new system (a `template` or a single `stage`) and link `cell_id` to its
    first cell that accepts it, e.g. a second environment from the same mission, or phase 1
    from a TCS concept. Use list_branch_targets or list_branch_options first."""
    return await call(
        "branch_cell",
        path={"cell_id": cell_id},
        json={**_blueprint(template, stage), "name": name, "justification": justification},
    )


@_tool("list_branch_options")
async def list_branch_options(cell_id: str) -> list[Json]:
    """Templates and stages that can be branched from `cell_id`."""
    return await call("list_branch_options", path={"cell_id": cell_id})


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


@_tool("get_cell_context")
async def get_cell_context(cell_id: str) -> Json:
    """Resolved context of a cell: which cell provides each upstream stage type, and the
    required stage types that are still missing (the cell cannot run until they are linked)."""
    return await call("get_cell_context", path={"cell_id": cell_id})


@_tool("link_cells")
async def link_cells(source_cell_id: str, target_cell_id: str, justification: str) -> Json:
    """Link two cells: the target gets the source and its whole context. A cell has one parent,
    or several only if their contexts share no stage type (union); roots (mission, equipment)
    have none; no stage type may repeat; types follow the catalog order. Use
    list_link_targets first."""
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


# ---------------------------------------------------------------- form artifacts


@_tool("get_cell_artifact")
async def get_cell_artifact(cell_id: str) -> Json:
    """The applied artifact of a form cell (mission) or the applied parameters of a computation
    cell (environment: design values, dispersion, sampling, custom conditions): values in SI
    units, validation problems ({path, code, message}), per-field provenance ({source,
    change_id}), status and context. Start from this artifact to build a draft."""
    return await call("get_cell_artifact", path={"cell_id": cell_id})


@_tool("validate_cell_artifact")
async def validate_cell_artifact(cell_id: str, artifact: Json) -> Json:
    """Dry run: the problems a draft artifact would have. Changes nothing. The draft is the
    whole artifact (possibly incomplete), as returned by get_cell_artifact."""
    return await call(
        "validate_cell_artifact", path={"cell_id": cell_id}, json={"artifact": artifact}
    )


@_tool("apply_cell_artifact")
async def apply_cell_artifact(cell_id: str, artifact: Json, justification: str) -> Json:
    """Replace a form cell's artifact (or a computation cell's parameters) with the draft, in
    one undoable change. The justification is required. Problems are allowed (a form cell is
    then failed); everything downstream (and a computation cell itself) becomes outdated if the
    content changed; `change` is null if nothing changed. Keep the ids of existing list items
    (attitude_modes[].id, custom_conditions[].id); new items get ids."""
    return await call(
        "apply_cell_artifact",
        path={"cell_id": cell_id},
        json={"artifact": artifact, "justification": justification},
    )


# ---------------------------------------------------------------- computation stages


@_tool("update_cell")
async def update_cell(cell_id: str, justification: str = "") -> Json:
    """Update (run) a computation cell (environment) with its applied parameters and its
    context, in one undoable change; the justification is optional. Returns the change (null if
    it was already up to date or fails the same way), the project view and the cell's result:
    `up_to_date` with the new result, or `failed` with problems (`missing`, `context_invalid`,
    invalid parameters, `eccentricity_out_of_range`). Edit the parameters first with
    get_cell_artifact / apply_cell_artifact. Never compute environment numbers yourself."""
    return await call(
        "update_cell", path={"cell_id": cell_id}, json={"justification": justification}
    )


@_tool("get_cell_result")
async def get_cell_result(cell_id: str) -> Json:
    """Status, problems, provenance and last result of a computation cell (possibly outdated:
    check `status`). Environment: β and eclipse along the mission, ranges (irradiance, β,
    altitude, albedo, IR), extreme and custom conditions, and incident fluxes per condition,
    attitude mode and face (orbit average and peak, at the minimum and maximum design values,
    W/m²). SI units, angles in rad. Orbit profiles are listed; read one with
    get_orbit_profile."""
    return await call("get_cell_result", path={"cell_id": cell_id})


@_tool("get_orbit_profile")
async def get_orbit_profile(cell_id: str, condition_id: str, mode_id: str) -> Json:
    """One orbit of an environment condition in an attitude mode (ids from get_cell_result):
    time (s), inertial position (m) and velocity (m/s), Sun unit vector, sunlit fraction, body
    quaternion (body → inertial, [w, x, y, z]), Earth rotation angle and incident fluxes per
    face along the orbit (W/m²)."""
    return await call(
        "get_orbit_profile",
        path={"cell_id": cell_id},
        params={"condition_id": condition_id, "mode_id": mode_id},
    )


# ---------------------------------------------------------------- clipboard


@_tool("copy_to_clipboard")
async def copy_to_clipboard(
    system_ids: list[str] | None = None, cell_ids: list[str] | None = None
) -> Json:
    """Copy whole systems and/or loose cells as a versioned fragment (changes nothing).
    Keep the returned fragment and pass it to paste_from_clipboard, in this or another project.
    To cut, copy and then delete_system / delete_cell."""
    return await call(
        "copy_to_clipboard", json={"system_ids": system_ids or [], "cell_ids": cell_ids or []}
    )


@_tool("paste_from_clipboard")
async def paste_from_clipboard(
    fragment: Json,
    justification: str,
    x: float | None = None,
    y: float | None = None,
    target_system_id: str | None = None,
) -> Json:
    """Paste a fragment from copy_to_clipboard: new ids, internal links kept, links to cells
    outside the fragment dropped, cells never run. One undoable change. (x, y) places the
    top-left system; loose cells go into `target_system_id` or into a new system."""
    return await call(
        "paste_from_clipboard",
        json={
            "fragment": fragment,
            "position": _position(x, y),
            "target_system_id": target_system_id,
            "justification": justification,
        },
    )


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
