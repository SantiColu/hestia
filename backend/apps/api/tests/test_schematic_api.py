from typing import Any

from fastapi.testclient import TestClient

AGENT = {"X-Hestia-Actor": "stefan", "X-Hestia-Actor-Kind": "agent"}


def _cells(view: dict[str, Any], system_name: str) -> dict[str, dict[str, Any]]:
    project = view["project"]
    system = next(s for s in project["systems"] if s["name"] == system_name)
    return {c["stage"]: c for c in project["cells"] if c["id"] in system["cell_ids"]}


def _create(client: TestClient, **body: Any) -> dict[str, Any]:
    response = client.post("/project/systems", json={"justification": "", **body})
    assert response.status_code == 200, response.text
    return response.json()


def test_writes_need_an_open_project(client: TestClient) -> None:
    response = client.post("/project/systems", json={"template": "phase_0", "justification": ""})
    assert response.status_code == 409
    assert response.json()["code"] == "no_project_open"


def test_create_from_template_records_author(opened: TestClient) -> None:
    response = opened.post(
        "/project/systems",
        json={"template": "phase_0", "justification": "baseline"},
        headers=AGENT,
    )
    body = response.json()
    change = body["change"]
    assert change["author"] == {"kind": "agent", "name": "stefan"}
    assert change["justification"] == "baseline"
    assert change["operation"] == "create_system"
    project = body["view"]["project"]
    assert len(project["cells"]) == 5 and len(project["links"]) == 4
    assert all(c["status"] == "never_run" for c in project["cells"])
    assert body["view"]["document"]["dirty"] is True
    assert body["view"]["document"]["can_undo"] is True


def test_default_author_is_a_human(opened: TestClient) -> None:
    change = _create(opened, stage="mission")["change"]
    assert change["author"]["kind"] == "human"
    assert change["author"]["name"]


def test_blueprint_needs_exactly_one_of_template_or_stage(opened: TestClient) -> None:
    both = {"template": "phase_0", "stage": "mission", "justification": ""}
    assert opened.post("/project/systems", json=both).status_code == 422
    assert opened.post("/project/systems", json={"justification": ""}).status_code == 422


def test_link_validation_and_targets(opened: TestClient) -> None:
    _create(opened, template="phase_0", name="F0")
    view = _create(opened, template="phase_1", name="F1")["view"]
    f0, f1 = _cells(view, "F0"), _cells(view, "F1")

    targets = opened.get(f"/project/cells/{f0['mission']['id']}/link-targets").json()
    # Discretization has no parent; the rest of phase 1 accepts mission by union.
    assert set(targets["cell_ids"]) == {c["id"] for c in f1.values()}

    bad = opened.post(
        "/project/links",
        json={
            "source_cell_id": f1["sensitivity"]["id"],
            "target_cell_id": f0["mission"]["id"],
            "justification": "",
        },
    )
    assert bad.status_code == 422
    assert bad.json()["code"] == "invalid_operation"

    good = opened.post(
        "/project/links",
        json={
            "source_cell_id": f0["environment"]["id"],
            "target_cell_id": f1["load_cases"]["id"],
            "justification": "hot/cold cases",
        },
    )
    assert good.status_code == 200
    link_id = good.json()["change"]["created_ids"][0]

    no_reason = opened.request(
        "DELETE", f"/project/links/{link_id}", json={"justification": ""}, headers=AGENT
    )
    assert no_reason.status_code == 422
    assert no_reason.json()["code"] == "justification_required"
    # Humans are never asked for a justification (ADR 0024).
    ok = opened.request("DELETE", f"/project/links/{link_id}", json={"justification": ""})
    assert ok.status_code == 200


def test_branch_and_targets(opened: TestClient) -> None:
    view = _create(opened, template="phase_0", name="F0")["view"]
    f0 = _cells(view, "F0")
    targets = opened.get("/project/branch-targets", params={"stage": "environment"}).json()
    assert targets["cell_ids"] == [f0["mission"]["id"]]
    assert opened.get("/project/branch-targets").status_code == 422

    response = opened.post(
        f"/project/cells/{f0['mission']['id']}/branch",
        json={"stage": "environment", "name": "SSO800", "justification": ""},
    )
    assert response.status_code == 200
    project = response.json()["view"]["project"]
    new_env = _cells(response.json()["view"], "SSO800")["environment"]
    assert {"source": f0["mission"]["id"], "target": new_env["id"]} in [
        {"source": lk["source_cell_id"], "target": lk["target_cell_id"]} for lk in project["links"]
    ]

    options = opened.get(f"/project/cells/{f0['global_balance']['id']}/branch-options").json()
    assert options == [
        {"template": "phase_1", "stage": None},
        *(
            {"template": None, "stage": s}
            for s in (
                "tcs_concept",
                "discretization",
                "couplings",
                "load_cases",
                "solution",
                "margins",
                "sensitivity",
            )
        ),
    ]

    invalid = opened.post(
        f"/project/cells/{f0['tcs_concept']['id']}/branch",
        json={"template": "phase_0", "justification": ""},
    )
    assert invalid.status_code == 422


def test_rename_move_add_duplicate_delete(opened: TestClient) -> None:
    view = _create(opened, stage="mission", name="Sys")["view"]
    system_id = view["project"]["systems"][0]["id"]

    renamed = opened.patch(
        f"/project/systems/{system_id}", json={"name": "Base", "justification": ""}
    )
    assert renamed.json()["view"]["project"]["systems"][0]["name"] == "Base"

    moved = opened.post(
        f"/project/systems/{system_id}/move",
        json={"position": {"x": 5, "y": 7}, "justification": ""},
    )
    assert moved.json()["view"]["project"]["systems"][0]["position"] == {"x": 5.0, "y": 7.0}

    added = opened.post(
        f"/project/systems/{system_id}/cells", json={"stage": "environment", "justification": ""}
    )
    project = added.json()["view"]["project"]
    assert len(project["cells"]) == 2 and len(project["links"]) == 1
    cell_id = project["cells"][1]["id"]

    cell = opened.patch(f"/project/cells/{cell_id}", json={"name": "LEO600", "justification": ""})
    assert cell.json()["view"]["project"]["cells"][1]["name"] == "LEO600"

    dup = opened.post(f"/project/systems/{system_id}/duplicate", json={"justification": ""})
    assert len(dup.json()["view"]["project"]["systems"]) == 2

    assert (
        opened.request(
            "DELETE", f"/project/cells/{cell_id}", json={"justification": ""}, headers=AGENT
        ).status_code
        == 422
    )
    deleted = opened.request(
        "DELETE", f"/project/cells/{cell_id}", json={"justification": "not needed"}
    )
    assert len(deleted.json()["view"]["project"]["cells"]) == 3

    gone = opened.request(
        "DELETE", f"/project/systems/{system_id}", json={"justification": "cleanup"}
    )
    assert [s["name"] for s in gone.json()["view"]["project"]["systems"]] == ["Base (copia)"]

    missing = opened.patch("/project/cells/cell_nope", json={"name": "x", "justification": ""})
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


def test_move_and_delete_a_selection_in_one_change(opened: TestClient) -> None:
    first = _create(opened, stage="mission", name="A")["view"]["project"]["systems"][0]["id"]
    project = _create(opened, stage="mission", name="B")["view"]["project"]
    ids = [system["id"] for system in project["systems"]]
    assert first in ids

    moves = [{"system_id": sid, "position": {"x": 10.0 * i, "y": 0.0}} for i, sid in enumerate(ids)]
    moved = opened.post("/project/systems/move", json={"moves": moves})
    assert moved.status_code == 200
    assert [s["position"]["x"] for s in moved.json()["view"]["project"]["systems"]] == [0, 10]

    no_reason = opened.post("/project/delete", json={"system_ids": ids}, headers=AGENT)
    assert no_reason.json()["code"] == "justification_required"
    deleted = opened.post("/project/delete", json={"system_ids": ids})
    assert deleted.status_code == 200
    assert deleted.json()["view"]["project"]["systems"] == []
    assert deleted.json()["change"]["operation"] == "delete_items"

    opened.post("/project/undo", json={})
    assert len(opened.get("/session").json()["project"]["project"]["systems"]) == 2


def test_undo_redo_and_history(opened: TestClient) -> None:
    _create(opened, template="phase_0")
    assert opened.post("/project/redo", json={"justification": ""}).status_code == 409

    undone = opened.post("/project/undo", json={"justification": "mistake"}, headers=AGENT)
    assert undone.json()["view"]["project"]["systems"] == []
    assert undone.json()["view"]["document"]["can_redo"] is True

    redone = opened.post("/project/redo", json={"justification": ""})
    assert len(redone.json()["view"]["project"]["systems"]) == 1

    history = opened.get("/project/history").json()
    assert [c["operation"] for c in history] == ["create_system", "undo", "redo"]
    assert history[1]["author"]["kind"] == "agent"
    assert history[1]["reverts"] == history[0]["id"]


def test_cell_context_and_missing(opened: TestClient) -> None:
    view = _create(opened, template="phase_1", name="F1")["view"]
    f1 = _cells(view, "F1")
    disc = f1["discretization"]["id"]
    assert view["missing"][disc] == ["mission", "equipment", "tcs_concept"]
    assert f1["couplings"]["id"] not in view["missing"]

    context = opened.get(f"/project/cells/{f1['load_cases']['id']}/context").json()
    assert [e["stage"] for e in context["entries"]] == ["discretization", "couplings"]
    assert context["entries"][0]["cell_id"] == disc
    assert context["missing"] == ["mission", "environment", "equipment"]
    assert opened.get("/project/cells/nope/context").status_code == 404
