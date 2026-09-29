from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from hestia_project.workspace import EventType, ProjectEvent

AGENT = {"X-Hestia-Actor": "stefan", "X-Hestia-Actor-Kind": "agent"}


def _phase0(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/project/systems", json={"template": "phase_0", "name": "F0", "justification": ""}
    )
    assert response.status_code == 200, response.text
    return response.json()["view"]


def _copy(client: TestClient, **body: Any) -> dict[str, Any]:
    response = client.post("/project/clipboard/copy", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_copy_returns_a_fragment_and_changes_nothing(opened: TestClient) -> None:
    view = _phase0(opened)
    fragment = _copy(opened, system_ids=[view["project"]["systems"][0]["id"]])
    assert fragment["kind"] == "hestia.fragment"
    assert fragment["schema_version"] == 1
    assert len(fragment["systems"][0]["cells"]) == 5 and len(fragment["links"]) == 4
    session = opened.get("/session").json()["project"]
    assert session["document"]["revision"] == view["document"]["revision"]
    assert len(opened.get("/project/history").json()) == 1


def test_paste_is_one_change_with_author_and_undo_label(opened: TestClient) -> None:
    view = _phase0(opened)
    fragment = _copy(opened, system_ids=[view["project"]["systems"][0]["id"]])
    response = opened.post(
        "/project/clipboard/paste",
        json={"fragment": fragment, "position": {"x": 900, "y": 0}, "justification": "variant"},
        headers=AGENT,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["change"]["operation"] == "paste"
    assert body["change"]["author"] == {"kind": "agent", "name": "stefan"}
    assert body["change"]["justification"] == "variant"
    project = body["view"]["project"]
    assert [s["name"] for s in project["systems"]] == ["F0", "F0 (2)"]
    assert project["systems"][1]["position"] == {"x": 900, "y": 0}
    assert len(project["links"]) == 8
    document = body["view"]["document"]
    assert document["undo_label"] == "pegar"

    undone = opened.post("/project/undo", json={"justification": ""}).json()["view"]
    assert len(undone["project"]["systems"]) == 1
    assert undone["document"]["redo_label"] == "pegar"
    assert undone["document"]["undo_label"] == "crear sistema"


def test_paste_into_a_system(opened: TestClient) -> None:
    view = _phase0(opened)
    system = view["project"]["systems"][0]
    fragment = _copy(opened, cell_ids=[system["cell_ids"][0]])
    body = opened.post(
        "/project/clipboard/paste",
        json={"fragment": fragment, "target_system_id": system["id"], "justification": ""},
    ).json()
    assert len(body["view"]["project"]["systems"][0]["cell_ids"]) == 6


def test_paste_in_another_project_and_reopen(opened: TestClient, tmp_path: Path) -> None:
    view = _phase0(opened)
    fragment = _copy(opened, system_ids=[view["project"]["systems"][0]["id"]])
    assert opened.post("/project/new", json={"discard_unsaved": True}).status_code == 200
    pasted = opened.post(
        "/project/clipboard/paste", json={"fragment": fragment, "justification": ""}
    ).json()["view"]["project"]
    path = tmp_path / "other.hestia"
    assert opened.post("/project/save-as", json={"path": str(path)}).status_code == 200
    assert opened.post("/project/close", json={}).status_code == 200
    reopened = opened.post("/project/open", json={"path": str(path)}).json()["project"]
    assert reopened["systems"] == pasted["systems"]
    assert reopened["cells"] == pasted["cells"]
    assert reopened["links"] == pasted["links"]


def test_unknown_fragment_version_is_rejected(opened: TestClient) -> None:
    view = _phase0(opened)
    fragment = _copy(opened, system_ids=[view["project"]["systems"][0]["id"]])
    fragment["schema_version"] = 2
    response = opened.post(
        "/project/clipboard/paste", json={"fragment": fragment, "justification": ""}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_fragment"
    assert len(opened.get("/project/history").json()) == 1


def test_not_a_fragment_is_rejected(opened: TestClient) -> None:
    response = opened.post(
        "/project/clipboard/paste",
        json={"fragment": {"kind": "text", "systems": []}, "justification": ""},
    )
    assert response.status_code == 422


def test_copy_nothing_or_unknown(opened: TestClient) -> None:
    assert opened.post("/project/clipboard/copy", json={}).json()["code"] == "invalid_operation"
    assert opened.post("/project/clipboard/copy", json={"cell_ids": ["x"]}).status_code == 404


def test_paste_emits_a_project_changed_event(opened: TestClient) -> None:
    view = _phase0(opened)
    fragment = _copy(opened, system_ids=[view["project"]["systems"][0]["id"]])
    received: list[ProjectEvent] = []
    opened.app.state.workspace.subscribe(received.append)  # type: ignore[attr-defined]
    opened.post("/project/clipboard/paste", json={"fragment": fragment, "justification": ""})
    assert [e.type for e in received] == [EventType.PROJECT_CHANGED]
    assert received[0].change is not None and received[0].change.operation == "paste"
    assert received[0].message == "Pegó el sistema «F0 (2)»."
