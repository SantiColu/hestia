"""Each tool issues exactly the API request it maps to (mocked HTTP transport)."""

import asyncio
import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from hestia_mcp import api
from hestia_mcp.server import server

Captured = list[httpx.Request]


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> Iterator[Captured]:
    requests: Captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        lists = ("/recents", "/project/history")
        is_list = request.url.path in lists or request.url.path.endswith("/branch-options")
        body: Any = [] if is_list else {"ok": True}
        return httpx.Response(200, json=body)

    def client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url="http://hestia.test",
            transport=httpx.MockTransport(handler),
            headers={"X-Hestia-Actor-Kind": "agent", "X-Hestia-Actor": "test-agent"},
        )

    monkeypatch.setattr(api, "api_client", client)
    yield requests


J = {"justification": "because"}
FRAGMENT: dict[str, Any] = {
    "kind": "hestia.fragment",
    "schema_version": 1,
    "systems": [],
    "links": [],
}

ARTIFACT: dict[str, Any] = {"orbit": {"type": "sso", "altitude": 600000.0}}

CASES: list[tuple[str, dict[str, Any], str, str, dict[str, Any] | None]] = [
    ("ping", {}, "GET", "/health", None),
    ("get_catalog", {}, "GET", "/catalog", None),
    (
        "get_artifact_schema",
        {"stage": "mission"},
        "GET",
        "/catalog/stages/mission/artifact-schema",
        None,
    ),
    ("get_session", {}, "GET", "/session", None),
    ("list_recent_projects", {}, "GET", "/recents", None),
    ("remove_recent_project", {"path": "/a.hestia"}, "DELETE", "/recents", {"path": "/a.hestia"}),
    ("new_project", {}, "POST", "/project/new", {"name": None, "discard_unsaved": False}),
    (
        "open_project",
        {"path": "/a.hestia", "force": True},
        "POST",
        "/project/open",
        {"path": "/a.hestia", "force": True, "discard_unsaved": False},
    ),
    ("save_project", {}, "POST", "/project/save", None),
    ("save_project_as", {"path": "/b"}, "POST", "/project/save-as", {"path": "/b"}),
    ("close_project", {}, "POST", "/project/close", {"discard_unsaved": False}),
    ("get_history", {}, "GET", "/project/history", None),
    ("undo", J, "POST", "/project/undo", J),
    ("redo", J, "POST", "/project/redo", J),
    (
        "create_system",
        {"template": "phase_0", "x": 1, "y": 2, **J},
        "POST",
        "/project/systems",
        {
            "template": "phase_0",
            "stage": None,
            "name": None,
            "position": {"x": 1, "y": 2},
            **J,
        },
    ),
    (
        "rename_system",
        {"system_id": "s1", "name": "Base", **J},
        "PATCH",
        "/project/systems/s1",
        {"name": "Base", **J},
    ),
    (
        "move_system",
        {"system_id": "s1", "x": 3, "y": 4, **J},
        "POST",
        "/project/systems/s1/move",
        {"position": {"x": 3, "y": 4}, **J},
    ),
    ("duplicate_system", {"system_id": "s1", **J}, "POST", "/project/systems/s1/duplicate", J),
    ("delete_system", {"system_id": "s1", **J}, "DELETE", "/project/systems/s1", J),
    (
        "add_cell",
        {"system_id": "s1", "stage": "environment", **J},
        "POST",
        "/project/systems/s1/cells",
        {"stage": "environment", "name": None, **J},
    ),
    (
        "rename_cell",
        {"cell_id": "c1", "name": "LEO", **J},
        "PATCH",
        "/project/cells/c1",
        {"name": "LEO", **J},
    ),
    ("delete_cell", {"cell_id": "c1", **J}, "DELETE", "/project/cells/c1", J),
    (
        "branch_cell",
        {"cell_id": "c1", "stage": "environment", **J},
        "POST",
        "/project/cells/c1/branch",
        {"template": None, "stage": "environment", "name": None, **J},
    ),
    ("list_link_targets", {"cell_id": "c1"}, "GET", "/project/cells/c1/link-targets", None),
    ("list_branch_options", {"cell_id": "c1"}, "GET", "/project/cells/c1/branch-options", None),
    ("list_branch_targets", {"template": "phase_1"}, "GET", "/project/branch-targets", None),
    ("get_cell_context", {"cell_id": "c1"}, "GET", "/project/cells/c1/context", None),
    (
        "link_cells",
        {"source_cell_id": "a", "target_cell_id": "b", **J},
        "POST",
        "/project/links",
        {"source_cell_id": "a", "target_cell_id": "b", **J},
    ),
    ("unlink_cells", {"link_id": "l1", **J}, "DELETE", "/project/links/l1", J),
    ("get_cell_artifact", {"cell_id": "c1"}, "GET", "/project/cells/c1/artifact", None),
    (
        "validate_cell_artifact",
        {"cell_id": "c1", "artifact": ARTIFACT},
        "POST",
        "/project/cells/c1/artifact/validate",
        {"artifact": ARTIFACT},
    ),
    (
        "apply_cell_artifact",
        {"cell_id": "c1", "artifact": ARTIFACT, **J},
        "PUT",
        "/project/cells/c1/artifact",
        {"artifact": ARTIFACT, **J},
    ),
    ("update_cell", {"cell_id": "c1"}, "POST", "/project/cells/c1/update", {"justification": ""}),
    ("update_cell", {"cell_id": "c1", **J}, "POST", "/project/cells/c1/update", J),
    ("get_cell_result", {"cell_id": "c1"}, "GET", "/project/cells/c1/result", None),
    (
        "get_orbit_profile",
        {"cell_id": "c1", "condition_id": "max_eclipse", "mode_id": "m1"},
        "GET",
        "/project/cells/c1/result/orbit-profile",
        None,
    ),
    (
        "copy_to_clipboard",
        {"system_ids": ["s1"]},
        "POST",
        "/project/clipboard/copy",
        {"system_ids": ["s1"], "cell_ids": []},
    ),
    (
        "paste_from_clipboard",
        {"fragment": FRAGMENT, "x": 5, "y": 6, **J},
        "POST",
        "/project/clipboard/paste",
        {"fragment": FRAGMENT, "position": {"x": 5, "y": 6}, "target_system_id": None, **J},
    ),
]


def test_cases_cover_every_tool() -> None:
    tools = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {case[0] for case in CASES} == tools


@pytest.mark.parametrize(("tool", "args", "method", "path", "body"), CASES)
def test_tool_request(
    captured: Captured,
    tool: str,
    args: dict[str, Any],
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    result = asyncio.run(server.call_tool(tool, args))
    assert not getattr(result, "is_error", False)
    (request,) = captured
    assert request.method == method
    assert request.url.path == path
    assert request.headers["X-Hestia-Actor-Kind"] == "agent"
    if body is None:
        assert request.content == b""
    else:
        assert json.loads(request.content) == body


def test_orbit_profile_query(captured: Captured) -> None:
    args = {"cell_id": "c1", "condition_id": "max_eclipse", "mode_id": "m1"}
    asyncio.run(server.call_tool("get_orbit_profile", args))
    assert dict(captured[0].url.params) == {"condition_id": "max_eclipse", "mode_id": "m1"}


def test_branch_targets_query(captured: Captured) -> None:
    asyncio.run(server.call_tool("list_branch_targets", {"stage": "margins"}))
    assert captured[0].url.params["stage"] == "margins"


def test_api_errors_become_tool_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            423, json={"code": "project_locked", "message": "abierto en otra instancia"}
        )

    monkeypatch.setattr(
        api,
        "api_client",
        lambda: httpx.AsyncClient(base_url="http://t", transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ToolError, match="project_locked: abierto en otra instancia"):
        asyncio.run(server.call_tool("open_project", {"path": "/a.hestia"}))


def test_default_headers_identify_the_agent() -> None:
    client = api.api_client()
    assert client.headers["X-Hestia-Actor-Kind"] == "agent"
    assert client.headers["X-Hestia-Actor"] == api.AGENT_NAME
    asyncio.run(client.aclose())
