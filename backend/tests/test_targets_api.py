"""POST /api/targets against real MySQL. Needs TEST_DATABASE_URL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.adapters.identity import InvalidTokenError, VerifiedIdentity
from app.auth import get_token_verifier
from app.db import get_session
from app.main import app
from app.models import PLATFORM_GOOGLE_MAPS, AnalysisTarget, User
from app.repositories.users import get_or_create_user
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


def saved_targets(db):
    db.rollback()  # end the snapshot so other sessions' commits are visible
    return db.scalars(select(AnalysisTarget)).all()


def user_id(db, uid):
    db.rollback()
    return db.scalar(select(User.id).where(User.firebase_uid == uid))


def test_create_target_is_owned_by_the_authenticated_user(client, db):
    response = client.post(
        "/api/targets",
        json={"name": "  Example Cafe  ", "source_url": GOOD_URL},
        headers=bearer("token-a"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Example Cafe"
    assert body["platform"] == PLATFORM_GOOGLE_MAPS
    assert body["source_url"] == GOOD_URL
    assert "owner_id" not in body
    stored = saved_targets(db)
    assert len(stored) == 1
    assert stored[0].id == body["id"]
    assert stored[0].owner_id == user_id(db, "uid-a")


def test_client_supplied_owner_and_platform_are_ignored(client, db):
    other = get_or_create_user(db, USER_B)

    response = client.post(
        "/api/targets",
        json={
            "name": "Example Cafe",
            "source_url": GOOD_URL,
            "owner_id": other.id,
            "user_id": other.id,
            "platform": "yelp",
        },
        headers={**bearer("token-a"), "X-Owner-Id": str(other.id)},
    )

    assert response.status_code == 201
    stored = saved_targets(db)
    assert len(stored) == 1
    assert stored[0].owner_id == user_id(db, "uid-a")
    assert stored[0].owner_id != other.id
    assert stored[0].platform == PLATFORM_GOOGLE_MAPS


def test_each_user_owns_only_their_own_target(client, db):
    for token, name in (("token-a", "A cafe"), ("token-b", "B cafe")):
        response = client.post(
            "/api/targets",
            json={"name": name, "source_url": GOOD_URL},
            headers=bearer(token),
        )
        assert response.status_code == 201

    owners = {t.name: t.owner_id for t in saved_targets(db)}
    assert owners["A cafe"] == user_id(db, "uid-a")
    assert owners["B cafe"] == user_id(db, "uid-b")
    assert owners["A cafe"] != owners["B cafe"]


@pytest.mark.parametrize(
    "headers", [{}, bearer("forged-token"), {"Authorization": "Basic abc"}]
)
def test_unauthenticated_create_is_rejected_and_saves_nothing(client, db, headers):
    response = client.post(
        "/api/targets",
        json={"name": "Example Cafe", "source_url": GOOD_URL},
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert saved_targets(db) == []


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"source_url": GOOD_URL}, "name"),
        ({"name": "   ", "source_url": GOOD_URL}, "name"),
        ({"name": "x" * 256, "source_url": GOOD_URL}, "name"),
        ({"name": "Cafe"}, "source_url"),
        ({"name": "Cafe", "source_url": "   "}, "source_url"),
        ({"name": "Cafe", "source_url": "not a url"}, "source_url"),
        (
            {"name": "Cafe", "source_url": "http://www.google.com/maps/place/x"},
            "source_url",
        ),
        (
            {"name": "Cafe", "source_url": "https://example.com/maps/place/x"},
            "source_url",
        ),
        (
            {"name": "Cafe", "source_url": "https://google.com.evil.example/maps/x"},
            "source_url",
        ),
        (
            {
                "name": "Cafe",
                "source_url": "https://www.google.com/maps/place/Example+Cafe",
            },
            "source_url",
        ),
        (
            {"name": "Cafe", "source_url": "https://maps.app.goo.gl/abc123"},
            "source_url",
        ),
    ],
)
def test_invalid_input_is_rejected_with_a_field_error_and_not_saved(
    client, db, payload, field
):
    response = client.post("/api/targets", json=payload, headers=bearer("token-a"))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert field in body["fieldErrors"]
    assert "Traceback" not in response.text
    assert saved_targets(db) == []


def test_place_id_url_is_accepted(client, db):
    url = (
        "https://www.google.com/maps/search/"
        "?api=1&query=Cafe&query_place_id=ChIJExample1"
    )

    response = client.post(
        "/api/targets",
        json={"name": "Cafe", "source_url": url},
        headers=bearer("token-a"),
    )

    assert response.status_code == 201
    assert len(saved_targets(db)) == 1


def test_database_failure_returns_a_safe_error_and_saves_nothing(
    client, db, monkeypatch
):
    def fail(*args, **kwargs):
        raise OperationalError("INSERT secret-sql", {}, Exception("db host down"))

    monkeypatch.setattr(targets_router, "create_target", fail)

    response = client.post(
        "/api/targets",
        json={"name": "Example Cafe", "source_url": GOOD_URL},
        headers=bearer("token-a"),
    )

    assert response.status_code == 500
    assert response.json()["code"] == "unexpected"
    assert "secret-sql" not in response.text
    assert "db host down" not in response.text
    assert saved_targets(db) == []
