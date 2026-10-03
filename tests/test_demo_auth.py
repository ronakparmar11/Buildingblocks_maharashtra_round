from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from blackbox.api import auth, demo
from blackbox.api.app import require_demo_session
from blackbox.config import get_settings


@pytest.fixture
def demo_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DEMO_AUTH_ENABLED", "1")
    monkeypatch.setenv("BLACKBOX_MOCK_API", "0")
    monkeypatch.setenv("DEMO_AUTH_SECRET", "test-only-secret")
    get_settings.cache_clear()
    app = FastAPI()
    app.middleware("http")(require_demo_session)
    app.include_router(auth.router, prefix="/api")
    app.include_router(demo.router, prefix="/api")
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_demo_session_protects_golden_flow(demo_client: TestClient) -> None:
    assert demo_client.get("/api/demo/golden").status_code == 401
    assert demo_client.post(
        "/api/auth/login",
        json={"email": "blackbox@gmail.com", "password": "wrong"},
    ).status_code == 401

    login = demo_client.post(
        "/api/auth/login",
        json={"email": "blackbox@gmail.com", "password": "blackbox123"},
    )
    assert login.status_code == 200
    assert login.json() == {
        "authenticated": True,
        "email": "blackbox@gmail.com",
    }

    golden = demo_client.get("/api/demo/golden")
    assert golden.status_code == 200
    assert len(golden.json()["run"]["steps"]) == 12
    assert golden.json()["repair"]["repaired"] is True

    assert demo_client.post("/api/auth/logout").status_code == 204
    assert demo_client.get("/api/demo/golden").status_code == 401