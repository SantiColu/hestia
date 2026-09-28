from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hestia_api.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(tmp_path / "home")) as test_client:
        yield test_client


@pytest.fixture
def opened(client: TestClient) -> TestClient:
    assert client.post("/project/new", json={}).status_code == 200
    return client
