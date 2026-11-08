import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import ConfigurationError


def test_health_reports_ok():
    response = TestClient(main.app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_stops_when_configuration_is_invalid(monkeypatch):
    def fail():
        raise ConfigurationError("missing or invalid configuration: DATABASE_URL")

    monkeypatch.setattr(main, "get_settings", fail)

    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        with TestClient(main.app):
            pass
