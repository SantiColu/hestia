import asyncio
import pathlib
import re

from hestia_mcp.api import OPERATIONS
from hestia_mcp.server import TOOL_OPERATIONS, server


def test_every_registered_tool_maps_to_an_operation() -> None:
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == set(TOOL_OPERATIONS)
    assert set(TOOL_OPERATIONS.values()) <= set(OPERATIONS)


PROJECT_CHANGES = {
    "undo",
    "redo",
    "create_system",
    "rename_system",
    "move_system",
    "duplicate_system",
    "delete_system",
    "add_cell",
    "rename_cell",
    "delete_cell",
    "branch_cell",
    "link_cells",
    "unlink_cells",
    "paste_from_clipboard",
    "apply_cell_artifact",
}


def test_write_tools_require_justification() -> None:
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    with_justification = {
        name
        for name, tool in tools.items()
        if "justification" in tool.input_schema.get("required", [])
    }
    assert with_justification == PROJECT_CHANGES


def test_no_backend_imports() -> None:
    """The MCP server talks HTTP only; it must never import backend packages."""
    forbidden = re.compile(
        r"^\s*(from|import)\s+hestia_(core|project|adapters|api)\b", re.MULTILINE
    )
    src = pathlib.Path(__file__).parents[1] / "src"
    offenders = [p for p in src.rglob("*.py") if forbidden.search(p.read_text())]
    assert offenders == []
