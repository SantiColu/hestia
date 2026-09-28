from pathlib import Path

from fastapi.testclient import TestClient

from hestia_api.main import create_app


def _add_system(client: TestClient) -> None:
    body = {"template": "phase_0", "justification": ""}
    assert client.post("/project/systems", json=body).status_code == 200


def test_session_lifecycle(client: TestClient, tmp_path: Path) -> None:
    assert client.get("/session").json() == {"project": None}

    view = client.post("/project/new", json={}).json()
    assert view["project"]["name"] == "Sin título"
    assert view["document"]["path"] is None
    _add_system(client)

    save = client.post("/project/save")
    assert save.status_code == 409 and save.json()["code"] == "no_path"

    close = client.post("/project/close", json={})
    assert close.status_code == 409 and close.json()["code"] == "unsaved_changes"

    target = tmp_path / "SAT-M1"
    saved = client.post("/project/save-as", json={"path": str(target)}).json()
    assert saved["document"]["file_name"] == "SAT-M1.hestia"
    assert saved["document"]["dirty"] is False

    assert client.post("/project/close", json={}).json() == {"project": None}

    opened = client.post("/project/open", json={"path": str(tmp_path / "SAT-M1.hestia")})
    assert opened.status_code == 200
    assert len(opened.json()["project"]["systems"]) == 1
    assert client.get("/session").json()["project"]["document"]["file_name"] == "SAT-M1.hestia"


def test_save_then_reopen_keeps_history(client: TestClient, tmp_path: Path) -> None:
    client.post("/project/new", json={})
    path = tmp_path / "a.hestia"
    client.post("/project/save-as", json={"path": str(path)})
    _add_system(client)
    assert client.get("/session").json()["project"]["document"]["dirty"] is True
    assert client.post("/project/save").json()["document"]["dirty"] is False
    client.post("/project/close", json={})
    client.post("/project/open", json={"path": str(path)})
    assert [c["operation"] for c in client.get("/project/history").json()] == ["create_system"]


def test_discard_unsaved(client: TestClient) -> None:
    client.post("/project/new", json={})
    _add_system(client)
    assert client.post("/project/new", json={}).status_code == 409
    fresh = client.post("/project/new", json={"discard_unsaved": True}).json()
    assert fresh["project"]["systems"] == []


def test_open_errors(client: TestClient, tmp_path: Path) -> None:
    missing = client.post("/project/open", json={"path": str(tmp_path / "nope.hestia")})
    assert missing.status_code == 422
    assert missing.json()["code"] == "invalid_project_file"
    junk = tmp_path / "junk.hestia"
    junk.write_text("not sqlite")
    assert client.post("/project/open", json={"path": str(junk)}).status_code == 422


def test_lock_between_instances(client: TestClient, tmp_path: Path) -> None:
    path = tmp_path / "shared.hestia"
    client.post("/project/new", json={})
    client.post("/project/save-as", json={"path": str(path)})

    with TestClient(create_app(tmp_path / "home2")) as other:
        locked = other.post("/project/open", json={"path": str(path)})
        assert locked.status_code == 423
        body = locked.json()
        assert body["code"] == "project_locked"
        assert "holder" in body["details"]
        forced = other.post("/project/open", json={"path": str(path), "force": True})
        assert forced.status_code == 200


def test_recents(client: TestClient, tmp_path: Path) -> None:
    for name in ("a", "b"):
        client.post("/project/new", json={"discard_unsaved": True})
        client.post("/project/save-as", json={"path": str(tmp_path / name)})
    client.post("/project/close", json={})
    (tmp_path / "a.hestia").unlink()

    recents = client.get("/recents").json()
    assert [(Path(r["path"]).name, r["exists"]) for r in recents] == [
        ("b.hestia", True),
        ("a.hestia", False),
    ]
    remaining = client.request("DELETE", "/recents", json={"path": recents[1]["path"]}).json()
    assert [Path(r["path"]).name for r in remaining] == ["b.hestia"]
