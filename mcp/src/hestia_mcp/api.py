"""HTTP access to the Hestia REST API. The only way this package touches Hestia.

``OPERATIONS`` maps each API ``operationId`` used by a tool to its method and path. The
parity test checks it against ``shared/openapi.json``.
"""

import os
from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

API_URL = os.environ.get("HESTIA_API_URL", "http://127.0.0.1:8000")
TIMEOUT_S = float(os.environ.get("HESTIA_API_TIMEOUT_S", "30"))
AGENT_NAME = os.environ.get("HESTIA_AGENT_NAME", "agente MCP")

OPERATIONS: dict[str, tuple[str, str]] = {
    "health": ("GET", "/health"),
    "get_catalog": ("GET", "/catalog"),
    "get_session": ("GET", "/session"),
    "list_recent_projects": ("GET", "/recents"),
    "remove_recent_project": ("DELETE", "/recents"),
    "new_project": ("POST", "/project/new"),
    "open_project": ("POST", "/project/open"),
    "save_project": ("POST", "/project/save"),
    "save_project_as": ("POST", "/project/save-as"),
    "close_project": ("POST", "/project/close"),
    "get_history": ("GET", "/project/history"),
    "undo": ("POST", "/project/undo"),
    "redo": ("POST", "/project/redo"),
    "create_system": ("POST", "/project/systems"),
    "rename_system": ("PATCH", "/project/systems/{system_id}"),
    "move_system": ("POST", "/project/systems/{system_id}/move"),
    "duplicate_system": ("POST", "/project/systems/{system_id}/duplicate"),
    "delete_system": ("DELETE", "/project/systems/{system_id}"),
    "add_cell": ("POST", "/project/systems/{system_id}/cells"),
    "rename_cell": ("PATCH", "/project/cells/{cell_id}"),
    "delete_cell": ("DELETE", "/project/cells/{cell_id}"),
    "branch_cell": ("POST", "/project/cells/{cell_id}/branch"),
    "list_link_targets": ("GET", "/project/cells/{cell_id}/link-targets"),
    "list_branch_targets": ("GET", "/project/branch-targets"),
    "link_cells": ("POST", "/project/links"),
    "unlink_cells": ("DELETE", "/project/links/{link_id}"),
}

NOT_TOOLS: dict[str, str] = {
    "stream_events": "Server-Sent Events for live UIs; agents read state and history instead.",
}
"""API operations deliberately without a tool, with the reason."""


def api_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=API_URL,
        timeout=TIMEOUT_S,
        headers={"X-Hestia-Actor-Kind": "agent", "X-Hestia-Actor": AGENT_NAME},
    )


async def call(
    operation_id: str,
    *,
    path: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """Call one API operation and return its JSON body.

    API errors become ``ToolError`` with the API's code and message, so the agent can react.
    """
    method, template = OPERATIONS[operation_id]
    url = template.format(**(path or {}))
    async with api_client() as client:
        try:
            response = await client.request(method, url, json=json, params=params)
        except httpx.HTTPError as exc:
            raise ToolError(f"Hestia API unreachable at {API_URL}: {exc}") from exc
    if response.is_error:
        try:
            body: Any = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict) and "code" in body:
            raise ToolError(f"{body['code']}: {body['message']}")
        raise ToolError(f"HTTP {response.status_code}: {response.text}")
    return response.json()
