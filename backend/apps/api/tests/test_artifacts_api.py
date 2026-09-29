"""Form artifacts over HTTP (ADR 0017): read, dry validation and apply."""

from typing import Any

from fastapi.testclient import TestClient

AGENT = {"X-Hestia-Actor": "stefan", "X-Hestia-Actor-Kind": "agent"}

DRAFT: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 157_788_000.0},
    "orbit": {"type": "sso", "altitude": 600000.0, "ltan": "10:30"},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
    "attitude_modes": [
        {
            "name": "Apuntado nadir",
            "primary_axis": "+Z",
            "primary_target": "nadir",
            "secondary_axis": "+X",
            "secondary_target": "velocity",
        }
    ],
}


def _phase0(client: TestClient) -> dict[str, str]:
    body = client.post("/project/systems", json={"template": "phase_0", "justification": ""}).json()
    return {c["stage"]: c["id"] for c in body["view"]["project"]["cells"]}


def test_read_defaults(opened: TestClient) -> None:
    cells = _phase0(opened)
    body = opened.get(f"/project/cells/{cells['mission']}/artifact").json()
    assert body["status"] == "never_run" and body["applied"] is False
    assert body["artifact"]["orbit"]["type"] == "sso"
    assert body["artifact"]["criteria"]["uncertainty_margin"] == 10.0
    assert body["provenance"]["orbit.type"]["source"] == "default"
    assert body["context"]["missing"] == []
    assert any(p["code"] == "required" for p in body["problems"])


def test_dry_validation_changes_nothing(opened: TestClient) -> None:
    cells = _phase0(opened)
    draft = {**DRAFT, "orbit": {"type": "sso", "altitude": 6.0e6, "ltan": "10:30"}}
    body = opened.post(
        f"/project/cells/{cells['mission']}/artifact/validate", json={"artifact": draft}
    ).json()
    assert body["problems"] == [
        {
            "path": "orbit.altitude",
            "code": "sso_altitude",
            "message": "No hay órbitas heliosincrónicas por encima de 5 974 km.",
        }
    ]
    assert len(opened.get("/project/history").json()) == 1
    session = opened.get("/session").json()["project"]
    assert session["document"]["revision"] == 1


def test_apply_undo_redo(opened: TestClient) -> None:
    cells = _phase0(opened)
    url = f"/project/cells/{cells['mission']}/artifact"
    missing = opened.put(url, json={"artifact": DRAFT, "justification": ""})
    assert missing.status_code == 422
    assert missing.json()["code"] == "justification_required"

    body = opened.put(
        url, json={"artifact": DRAFT, "justification": "datos del cliente"}, headers=AGENT
    ).json()
    change = body["change"]
    assert change["operation"] == "apply_artifact"
    assert change["author"] == {"kind": "agent", "name": "stefan"}
    assert body["cell"]["status"] == "up_to_date"
    assert body["cell"]["provenance"]["orbit.altitude"] == {
        "source": "entered",
        "change_id": change["id"],
    }
    assert body["cell"]["artifact"]["attitude_modes"][0]["id"].startswith("mode_")
    assert body["view"]["document"]["undo_label"] == "aplicar cambios"

    same = opened.put(url, json={"artifact": body["cell"]["artifact"], "justification": "x"})
    assert same.status_code == 200 and same.json()["change"] is None

    opened.post("/project/undo", json={"justification": ""})
    assert opened.get(url).json()["status"] == "never_run"
    opened.post("/project/redo", json={"justification": ""})
    assert opened.get(url).json()["status"] == "up_to_date"


def test_not_implemented_stages(opened: TestClient) -> None:
    cells = _phase0(opened)
    for stage in ("equipment", "global_balance"):
        response = opened.get(f"/project/cells/{cells[stage]}/artifact")
        assert response.status_code == 422
        assert response.json()["code"] == "stage_not_implemented"
    assert opened.get("/project/cells/nope/artifact").status_code == 404


def test_artifact_schema(client: TestClient) -> None:
    schema = client.get("/catalog/stages/mission/artifact-schema").json()
    orbit = schema["$defs"]["Orbit"]["properties"]
    assert orbit["altitude"]["x-unit"] == "m" and orbit["altitude"]["x-display-unit"] == "km"
    response = client.get("/catalog/stages/equipment/artifact-schema")
    assert response.status_code == 422
    assert response.json()["code"] == "stage_not_implemented"
