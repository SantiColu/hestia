"""The equipment stage over the generic artifact endpoints (ADR 0017, 0019, 0025)."""

from typing import Any

from fastapi.testclient import TestClient

AGENT = {"X-Hestia-Actor": "stefan", "X-Hestia-Actor-Kind": "agent"}

WHEEL: dict[str, Any] = {
    "id": "item_00a1",
    "name": "Rueda de reacción",
    "subsystem": "aocs",
    "quantity": 4,
    "mass": 0.9,
    "location": "internal",
    "modes": [
        {"id": "imode_00a1", "name": "Standby", "dissipation": 3.0},
        {"id": "imode_00a2", "name": "Pico", "dissipation": 20.0},
    ],
    "operating_min": 253.15,
    "operating_max": 333.15,
}
DRAFT: dict[str, Any] = {
    "items": [WHEEL],
    "operating_modes": [
        {"id": "opmode_00a1", "name": "Adquisición", "states": {"item_00a1": "imode_00a2"}}
    ],
}


def _phase0(client: TestClient) -> dict[str, str]:
    body = client.post("/project/systems", json={"template": "phase_0", "justification": ""}).json()
    return {c["stage"]: c["id"] for c in body["view"]["project"]["cells"]}


def test_catalog_marks_equipment_implemented(client: TestClient) -> None:
    stages = {s["stage"]: s for s in client.get("/catalog").json()["stages"]}
    assert stages["equipment"]["implemented"] is True


def test_read_defaults(opened: TestClient) -> None:
    cells = _phase0(opened)
    body = opened.get(f"/project/cells/{cells['equipment']}/artifact").json()
    assert body["status"] == "never_run" and body["applied"] is False
    [item] = body["artifact"]["items"]
    assert item["name"] == "Plataforma" and item["modes"][0]["name"] == "Nominal"
    [mode] = body["artifact"]["operating_modes"]
    assert mode["states"] == {item["id"]: item["modes"][0]["id"]}
    assert {"path": "items[0].mass", "code": "required", "message": "Falta la masa."} in body[
        "problems"
    ]


def test_dry_validation_reports_problems_by_path(opened: TestClient) -> None:
    cells = _phase0(opened)
    second = WHEEL | {"id": "item_00b1", "name": "rueda de reacción", "mass": -1}
    states = {"item_00a1": "imode_00a2", "item_00b1": None}
    draft = {"items": [WHEEL, second], "operating_modes": [{"name": "Nominal", "states": states}]}
    body = opened.post(
        f"/project/cells/{cells['equipment']}/artifact/validate", json={"artifact": draft}
    ).json()
    assert [(p["path"], p["code"]) for p in body["problems"]] == [
        ("items[1].name", "duplicate_name"),
        ("items[1].mass", "min"),
    ]
    assert body["problems"][0]["message"] == "Ya hay un equipo llamado «rueda de reacción»."
    assert len(opened.get("/project/history").json()) == 1


def test_agent_applies_a_whole_artifact_with_proposed_ids(opened: TestClient) -> None:
    cells = _phase0(opened)
    url = f"/project/cells/{cells['equipment']}/artifact"
    missing = opened.put(url, json={"artifact": DRAFT, "justification": ""}, headers=AGENT)
    assert missing.status_code == 422 and missing.json()["code"] == "justification_required"

    body = opened.put(
        url, json={"artifact": DRAFT, "justification": "hojas de datos"}, headers=AGENT
    ).json()
    assert body["change"]["operation"] == "apply_artifact"
    cell = body["cell"]
    assert cell["status"] == "up_to_date" and cell["problems"] == []
    assert cell["artifact"]["items"][0]["id"] == "item_00a1"
    assert cell["artifact"]["operating_modes"][0]["states"] == {"item_00a1": "imode_00a2"}

    opened.post("/project/undo", json={"justification": ""})
    assert opened.get(url).json()["status"] == "never_run"


def test_a_human_applies_with_problems_without_justification(opened: TestClient) -> None:
    cells = _phase0(opened)
    url = f"/project/cells/{cells['equipment']}/artifact"
    draft = DRAFT | {"items": [WHEEL | {"operating_max": 200.0}]}
    body = opened.put(url, json={"artifact": draft}).json()
    assert body["cell"]["status"] == "failed"
    assert [p["path"] for p in body["cell"]["problems"]] == ["items[0].operating_max"]


def test_artifact_schema(client: TestClient) -> None:
    schema = client.get("/catalog/stages/equipment/artifact-schema").json()
    item = schema["$defs"]["Item"]["properties"]
    assert item["operating_min"]["x-unit"] == "K"
    assert item["operating_min"]["x-display-unit"] == "°C"
    assert item["subsystem"]["x-enum-labels"]["aocs"] == "Control de actitud"
    assert schema["$defs"]["ItemMode"]["properties"]["dissipation"]["x-unit"] == "W"
    duration = schema["$defs"]["OperatingMode"]["properties"]["max_duration"]
    assert duration["x-display-unit"] == "h"


def test_dry_validation_reports_states_by_path(opened: TestClient) -> None:
    cells = _phase0(opened)
    states = {"item_00a1": "imode_zz", "item_gone": None}
    draft = DRAFT | {"operating_modes": [DRAFT["operating_modes"][0] | {"states": states}]}
    body = opened.post(
        f"/project/cells/{cells['equipment']}/artifact/validate", json={"artifact": draft}
    ).json()
    assert [(p["path"], p["code"]) for p in body["problems"]] == [
        ("operating_modes[0].states.item_00a1", "invalid_reference"),
        ("operating_modes[0].states.item_gone", "not_allowed"),
    ]


def test_a_replaced_id_breaks_the_reference_and_is_reported(opened: TestClient) -> None:
    cells = _phase0(opened)
    url = f"/project/cells/{cells['equipment']}/artifact"
    malformed = "Rueda-1"  # not `item_<hex>`: the backend replaces it (ADR 0025)
    draft: dict[str, Any] = {
        "items": [WHEEL | {"id": malformed}],
        "operating_modes": [
            {"id": "opmode_00a1", "name": "Adquisición", "states": {malformed: "imode_00a2"}}
        ],
    }
    body = opened.put(url, json={"artifact": draft, "justification": "x"}, headers=AGENT).json()
    cell = body["cell"]
    new_id = cell["artifact"]["items"][0]["id"]
    assert new_id.startswith("item_") and new_id != malformed
    assert cell["artifact"]["operating_modes"][0]["states"] == {malformed: "imode_00a2"}
    assert cell["status"] == "failed"
    assert [(p["path"], p["code"]) for p in cell["problems"]] == [
        (f"operating_modes[0].states.{new_id}", "required"),
        (f"operating_modes[0].states.{malformed}", "not_allowed"),
    ]
