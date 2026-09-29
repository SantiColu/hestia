import asyncio
import json
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from hestia_api.events import EventBroker
from hestia_api.main import create_app
from hestia_project.workspace import EventType, ProjectEvent


def test_broker_fans_out_to_subscribers() -> None:
    async def scenario() -> list[str]:
        broker = EventBroker()
        async with broker.subscribe() as first, broker.subscribe() as second:
            assert broker.subscriber_count == 2
            broker.publish(ProjectEvent(type=EventType.PROJECT_SAVED, message="saved"))
            got = [await asyncio.wait_for(q.get(), 1) for q in (first, second)]
        assert broker.subscriber_count == 0
        return [e.message for e in got]

    assert asyncio.run(scenario()) == ["saved", "saved"]


def test_workspace_changes_reach_the_broker(client: TestClient) -> None:
    received: list[ProjectEvent] = []
    client.app.state.workspace.subscribe(received.append)  # type: ignore[attr-defined]
    client.post("/project/new", json={})
    client.post("/project/systems", json={"stage": "mission", "justification": ""})
    assert [e.type for e in received] == [EventType.PROJECT_CREATED, EventType.PROJECT_CHANGED]
    assert received[1].change is not None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def live_api(tmp_path: Path) -> Iterator[str]:
    """The API served by a real uvicorn server (TestClient cannot end an endless stream)."""
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(tmp_path / "home"), port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def _next_event(lines: Iterator[str]) -> tuple[str, dict[str, Any]]:
    event = ""
    for line in lines:
        if line.startswith("event:"):
            event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            return event, json.loads(line.removeprefix("data:").strip())
    raise AssertionError("stream ended")


def test_sse_stream_reports_changes_from_any_client(live_api: str) -> None:
    with (
        httpx.Client(base_url=live_api, timeout=10) as client,
        client.stream("GET", "/events") as stream,
    ):
        assert stream.headers["content-type"].startswith("text/event-stream")
        lines = stream.iter_lines()
        event, data = _next_event(lines)
        assert event == "connected"
        assert data["type"] == "connected" and data["revision"] is None

        client.post("/project/new", json={})
        event, data = _next_event(lines)
        assert event == "project_created"

        client.post(
            "/project/systems",
            json={"template": "phase_0", "justification": "via agent"},
            headers={"X-Hestia-Actor-Kind": "agent", "X-Hestia-Actor": "stefan"},
        )
        event, data = _next_event(lines)
        assert event == "project_changed"
        assert data["revision"] == 1
        assert data["change"]["author"] == {"kind": "agent", "name": "stefan"}


def test_sse_stream_reports_a_paste(live_api: str) -> None:
    with httpx.Client(base_url=live_api, timeout=10) as client:
        client.post("/project/new", json={})
        view = client.post(
            "/project/systems", json={"template": "phase_0", "justification": ""}
        ).json()["view"]
        fragment = client.post(
            "/project/clipboard/copy", json={"system_ids": [view["project"]["systems"][0]["id"]]}
        ).json()
        with client.stream("GET", "/events") as stream:
            lines = stream.iter_lines()
            assert _next_event(lines)[0] == "connected"
            client.post(
                "/project/clipboard/paste",
                json={"fragment": fragment, "justification": "copy for a variant"},
                headers={"X-Hestia-Actor-Kind": "agent", "X-Hestia-Actor": "stefan"},
            )
            event, data = _next_event(lines)
            assert event == "project_changed"
            assert data["change"]["operation"] == "paste"
            assert data["change"]["justification"] == "copy for a variant"
