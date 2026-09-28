import asyncio

from hestia_mcp.server import server


def test_ping_tool_registered() -> None:
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {"ping"}


def test_no_backend_imports() -> None:
    """The MCP server talks HTTP only; it must never import backend packages."""
    import pathlib
    import re

    forbidden = re.compile(
        r"^\s*(from|import)\s+hestia_(core|project|adapters|api)\b", re.MULTILINE
    )
    src = pathlib.Path(__file__).parents[1] / "src"
    offenders = [p for p in src.rglob("*.py") if forbidden.search(p.read_text())]
    assert offenders == []
