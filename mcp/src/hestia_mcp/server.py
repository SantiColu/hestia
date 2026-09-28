"""Hestia MCP server.

Every tool maps to exactly one Hestia REST API operation. This module talks HTTP
only; it must never import backend packages.
"""

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from hestia_mcp import __version__

API_URL = os.environ.get("HESTIA_API_URL", "http://localhost:8000")
TIMEOUT_S = float(os.environ.get("HESTIA_API_TIMEOUT_S", "30"))

server = MCPServer(
    name="hestia",
    version=__version__,
    instructions=(
        "Hestia: preliminary thermal control system design for medium satellites. "
        "All numbers come from the Hestia API; never compute physical results yourself."
    ),
)


def api_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT_S)


@server.tool()
async def ping() -> dict[str, Any]:
    """Check that the Hestia API is reachable. Maps to GET /health."""
    async with api_client() as client:
        response = await client.get("/health")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
