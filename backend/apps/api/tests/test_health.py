from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_catalog(client: TestClient) -> None:
    body = client.get("/catalog").json()
    assert len(body["stages"]) == 10
    assert [t["id"] for t in body["templates"]] == ["phase_0", "phase_1"]
    load_cases = next(s for s in body["stages"] if s["stage"] == "load_cases")
    assert load_cases["inputs"] == ["couplings", "environment"]


def test_every_operation_has_a_stable_operation_id(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids))
    assert all("_" in i or i.isalpha() for i in ids)
