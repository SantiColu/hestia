"""Computation stages over HTTP (ADR 0021, 0023): parameters, update, result, orbit profiles
and the orbit preview of a draft."""

from typing import Any

from fastapi.testclient import TestClient

AGENT = {"X-Hestia-Actor": "stefan", "X-Hestia-Actor-Kind": "agent"}

MISSION: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 31_557_600.0},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
}
PARAMETERS: dict[str, Any] = {
    "orbit": {"type": "sso", "altitude": 600000.0, "ltan": "10:30"},
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


def _apply(client: TestClient, cell_id: str, artifact: dict[str, Any]) -> None:
    response = client.put(
        f"/project/cells/{cell_id}/artifact", json={"artifact": artifact, "justification": "datos"}
    )
    assert response.status_code == 200


def _phase0(
    client: TestClient,
    mission: dict[str, Any] | None = MISSION,
    parameters: dict[str, Any] | None = PARAMETERS,
) -> dict[str, str]:
    body = client.post("/project/systems", json={"template": "phase_0", "justification": ""}).json()
    cells = {c["stage"]: c["id"] for c in body["view"]["project"]["cells"]}
    if mission is not None:
        _apply(client, cells["mission"], mission)
    if parameters is not None:
        _apply(client, cells["environment"], parameters)
    return cells


def test_parameters_use_the_generic_artifact_endpoints(opened: TestClient) -> None:
    cells = _phase0(opened, parameters=None)
    env = cells["environment"]
    body = opened.get(f"/project/cells/{env}/artifact").json()
    assert body["stage"] == "environment" and body["applied"] is False
    assert body["artifact"]["design_values"]["solar_constant"] == 1361.0
    assert body["artifact"]["orbit"]["type"] == "sso"
    draft = {**body["artifact"], **PARAMETERS, "dispersion": {"geo_max_inclination": 0.1}}
    problems = opened.post(
        f"/project/cells/{env}/artifact/validate", json={"artifact": draft}
    ).json()["problems"]
    assert [p["code"] for p in problems] == ["not_allowed"]
    applied = opened.put(
        f"/project/cells/{env}/artifact",
        json={
            "artifact": {**body["artifact"], "sampling": {"orbit_samples": 72}},
            "justification": "x",
        },
    ).json()
    assert applied["change"]["operation"] == "apply_artifact"
    assert applied["cell"]["applied"] is True
    schema = opened.get("/catalog/stages/environment/artifact-schema").json()
    assert schema["$defs"]["Sampling"]["properties"]["mission_step"]["x-display-unit"] == "días"


def test_an_empty_draft_is_read_as_parameters(opened: TestClient) -> None:
    # {} matches both members of the body union; for an environment cell it is parameters.
    cells = _phase0(opened)
    response = opened.post(
        f"/project/cells/{cells['environment']}/artifact/validate", json={"artifact": {}}
    )
    assert response.status_code == 200
    assert {p["path"] for p in response.json()["problems"]} == {
        "orbit.altitude",
        "orbit.ltan",
        "attitude_modes",
    }


def test_an_orbit_is_only_valid_parameters(opened: TestClient) -> None:
    # The orbit and the attitude modes are environment parameters (ADR 0023): a mission cell
    # rejects them.
    cells = _phase0(opened)
    response = opened.post(
        f"/project/cells/{cells['mission']}/artifact/validate",
        json={"artifact": {**MISSION, "orbit": PARAMETERS["orbit"]}},
    )
    assert response.status_code == 422


def test_a_mission_draft_is_rejected_for_the_environment(opened: TestClient) -> None:
    cells = _phase0(opened)
    response = opened.post(
        f"/project/cells/{cells['environment']}/artifact/validate", json={"artifact": MISSION}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_operation"


def test_update_and_read_the_result(opened: TestClient) -> None:
    cells = _phase0(opened)
    env = cells["environment"]
    before = opened.get(f"/project/cells/{env}/result").json()
    assert before["status"] == "never_run" and before["environment"] is None

    body = opened.post(f"/project/cells/{env}/update", json={}, headers=AGENT).json()
    change = body["change"]
    assert change["operation"] == "update_cell" and change["justification"] == ""
    assert change["author"] == {"kind": "agent", "name": "stefan"}
    result = body["result"]
    assert result["status"] == "up_to_date" and result["problems"] == []
    assert result["provenance"]["provider"] == "analytic"
    assert result["provenance"]["context"][0]["cell_id"] == cells["mission"]
    environment = result["environment"]
    assert [c["id"] for c in environment["conditions"]] == ["max_eclipse", "min_eclipse"]
    ref = environment["orbit_profiles"][0]
    assert set(ref) == {"condition_id", "mode_id"}

    again = opened.post(f"/project/cells/{env}/update", json={"justification": "otra vez"})
    assert again.json()["change"] is None

    profile = opened.get(
        f"/project/cells/{env}/result/orbit-profile",
        params={"condition_id": ref["condition_id"], "mode_id": ref["mode_id"]},
    ).json()
    assert len(profile["time"]) == 120 and len(profile["quaternion"][0]) == 4
    assert [f["face"] for f in profile["faces"]] == ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
    missing = opened.get(
        f"/project/cells/{env}/result/orbit-profile",
        params={"condition_id": "nope", "mode_id": ref["mode_id"]},
    )
    assert missing.status_code == 404

    history = opened.get("/project/history").json()
    assert history[-1]["operation"] == "update_cell"
    undone = opened.post("/project/undo", json={"justification": ""})
    assert undone.status_code == 200
    assert opened.get(f"/project/cells/{env}/result").json()["status"] == "never_run"


def test_update_without_an_applied_mission_fails(opened: TestClient) -> None:
    cells = _phase0(opened, mission=None)
    body = opened.post(f"/project/cells/{cells['environment']}/update", json={}).json()
    assert body["result"]["status"] == "failed"
    assert [p["code"] for p in body["result"]["problems"]] == ["context_invalid"]


def test_form_stages_cannot_be_updated(opened: TestClient) -> None:
    cells = _phase0(opened)
    response = opened.post(f"/project/cells/{cells['mission']}/update", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "stage_not_implemented"
    assert opened.get(f"/project/cells/{cells['mission']}/result").status_code == 422


def test_preview_the_orbit_of_a_draft(opened: TestClient) -> None:
    cells = _phase0(opened, parameters=None)
    env = cells["environment"]
    revision = opened.get("/session").json()["project"]["document"]["revision"]
    body = opened.post(
        f"/project/cells/{env}/orbit-preview",
        json={"parameters": PARAMETERS, "date": "2028-06-01"},
    ).json()
    assert body["problems"] == []
    preview = body["preview"]
    assert preview["date"].startswith("2028-06-01") and preview["node_assumed"] is False
    assert preview["mode_id"] == "mode_1" and len(preview["quaternion"]) == 120
    assert opened.get("/session").json()["project"]["document"]["revision"] == revision

    broken = {**PARAMETERS, "orbit": {"type": "sso", "altitude": 600000.0}}
    failed = opened.post(f"/project/cells/{env}/orbit-preview", json={"parameters": broken})
    assert failed.json()["preview"] is None
    assert [p["path"] for p in failed.json()["problems"]] == ["orbit.ltan"]

    mission = opened.post(
        f"/project/cells/{cells['mission']}/orbit-preview", json={"parameters": PARAMETERS}
    )
    assert mission.status_code == 422 and mission.json()["code"] == "stage_not_implemented"
