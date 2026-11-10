"""GET /api/targets/{id} against real MySQL. Needs TEST_DATABASE_URL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.adapters.identity import InvalidTokenError, VerifiedIdentity
from app.auth import get_token_verifier
from app.db import get_session
from app.main import app
from app.models import PLATFORM_GOOGLE_MAPS, AnalysisTarget
from app.routers import targets as targets_router

USER_A = VerifiedIdentity(uid="uid-a", email="a@example.com")
USER_B = VerifiedIdentity(uid="uid-b", email="b@example.com")
GOOD_URL = "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2"


class FakeVerifier:
    tokens = {"token-a": USER_A, "token-b": USER_B}

    def verify(self, token):
        if token not in self.tokens:
            raise InvalidTokenError
        return self.tokens[token]

    def revoke(self, uid):
        pass


@pytest.fixture
def client(db, session_factory):
    def session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_token_verifier] = lambda: FakeVerifier()
    app.dependency_overrides[get_session] = session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def make_target(client, token, name):
    response = client.post(
        "/api/targets",
        json={"name": name, "source_url": GOOD_URL},
        headers=bearer(token),
    )
    assert response.status_code == 201
    return response.json()


def test_owner_can_open_their_target(client, db):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(f"/api/targets/{target['id']}", headers=bearer("token-a"))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target["id"]
    assert body["name"] == "A cafe"
    assert body["platform"] == PLATFORM_GOOGLE_MAPS
    assert body["source_url"] == GOOD_URL
    assert "owner_id" not in body


def test_another_users_target_is_denied_and_unchanged(client, db):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(f"/api/targets/{target['id']}", headers=bearer("token-b"))

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"
    assert "A cafe" not in response.text
    assert GOOD_URL not in response.text
    db.rollback()
    stored = db.scalars(select(AnalysisTarget)).all()
    assert [(t.id, t.name) for t in stored] == [(target["id"], "A cafe")]
    still_there = client.get(f"/api/targets/{target['id']}", headers=bearer("token-a"))
    assert still_there.status_code == 200


def test_missing_and_foreign_targets_get_identical_responses(client, db):
    target = make_target(client, "token-a", "A cafe")

    foreign = client.get(f"/api/targets/{target['id']}", headers=bearer("token-b"))
    missing = client.get("/api/targets/999999", headers=bearer("token-b"))

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


@pytest.mark.parametrize(
    "headers", [{}, bearer("forged-token"), {"Authorization": "Basic abc"}]
)
def test_unauthenticated_open_is_rejected_without_data(client, db, headers):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(f"/api/targets/{target['id']}", headers=headers)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert "A cafe" not in response.text


def test_open_database_failure_returns_a_safe_error(client, db, monkeypatch):
    def fail(*args, **kwargs):
        raise OperationalError("SELECT secret-sql", {}, Exception("db host down"))

    monkeypatch.setattr(targets_router, "get_target_for_owner", fail)

    response = client.get("/api/targets/1", headers=bearer("token-a"))

    assert response.status_code == 500
    assert response.json()["code"] == "unexpected"
    assert "secret-sql" not in response.text
    assert "db host down" not in response.text
