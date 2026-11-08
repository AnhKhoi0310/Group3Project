import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import ConfigurationError


def test_health_reports_ok():
    response = TestClient(main.app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def preflight(origin):
    return TestClient(main.app).options(
        "/api/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_configured_frontend_origin_may_call_the_api():
    response = preflight("http://localhost:5173")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_origin_is_not_allowed():
    response = preflight("http://evil.example")

    assert "access-control-allow-origin" not in response.headers


def test_startup_stops_when_configuration_is_invalid(monkeypatch):
    def fail():
        raise ConfigurationError("missing or invalid configuration: DATABASE_URL")

    monkeypatch.setattr(main, "get_settings", fail)

    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        with TestClient(main.app):
            pass
