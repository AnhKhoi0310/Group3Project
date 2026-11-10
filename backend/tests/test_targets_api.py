"""Tests for /api/targets against real MySQL. Needs TEST_DATABASE_URL."""

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
    db.rollback()
    return db.scalars(select(AnalysisTarget)).all()


def user_id(db, uid):
    db.rollback()
    return db.scalar(select(User.id).where(User.firebase_uid == uid))


def make_target(client, token, name):
    response = client.post(
        "/api/targets",
        json={"name": name, "source_url": GOOD_URL},
        headers=bearer(token),
    )
    assert response.status_code == 201
    return response.json()


# --- Create (S1-015) ---


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

    owners = {target.name: target.owner_id for target in saved_targets(db)}
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
    response = client.post(
        "/api/targets",
        json=payload,
        headers=bearer("token-a"),
    )

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
        raise OperationalError(
            "INSERT secret-sql",
            {},
            Exception("db host down"),
        )

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


# --- List (S1-017) ---


def test_each_user_sees_only_their_own_targets(client, db):
    a = make_target(client, "token-a", "A cafe")
    b = make_target(client, "token-b", "B cafe")

    response_a = client.get("/api/targets", headers=bearer("token-a"))
    response_b = client.get("/api/targets", headers=bearer("token-b"))

    assert response_a.status_code == 200
    assert [target["id"] for target in response_a.json()] == [a["id"]]
    assert response_b.status_code == 200
    assert [target["id"] for target in response_b.json()] == [b["id"]]
    assert "A cafe" not in response_b.text


def test_list_is_empty_for_a_user_with_no_targets(client, db):
    make_target(client, "token-a", "A cafe")

    response = client.get("/api/targets", headers=bearer("token-b"))

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_display_fields_and_hides_the_owner(client, db):
    make_target(client, "token-a", "A cafe")

    item = client.get(
        "/api/targets",
        headers=bearer("token-a"),
    ).json()[0]

    assert item["name"] == "A cafe"
    assert item["platform"] == PLATFORM_GOOGLE_MAPS
    assert item["source_url"] == GOOD_URL
    assert "owner_id" not in item


def test_list_is_newest_first(client, db):
    make_target(client, "token-a", "First")
    make_target(client, "token-a", "Second")

    response = client.get("/api/targets", headers=bearer("token-a"))

    assert [target["name"] for target in response.json()] == [
        "Second",
        "First",
    ]


@pytest.mark.parametrize(
    "headers", [{}, bearer("forged-token"), {"Authorization": "Basic abc"}]
)
def test_unauthenticated_list_is_rejected_without_data(client, db, headers):
    make_target(client, "token-a", "A cafe")

    response = client.get("/api/targets", headers=headers)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert "A cafe" not in response.text


def test_list_ignores_client_supplied_owner(client, db):
    a = make_target(client, "token-a", "A cafe")
    make_target(client, "token-b", "B cafe")

    response = client.get(
        f"/api/targets?owner_id={a['id']}&user_id={a['id']}",
        headers={
            **bearer("token-b"),
            "X-Owner-Id": str(a["id"]),
        },
    )

    assert [target["name"] for target in response.json()] == ["B cafe"]


def test_list_database_failure_returns_a_safe_error(client, db, monkeypatch):
    def fail(*args, **kwargs):
        raise OperationalError(
            "SELECT secret-sql",
            {},
            Exception("db host down"),
        )

    monkeypatch.setattr(targets_router, "list_targets_for_owner", fail)

    response = client.get("/api/targets", headers=bearer("token-a"))

    assert response.status_code == 500
    assert response.json()["code"] == "unexpected"
    assert "secret-sql" not in response.text
    assert "db host down" not in response.text


# --- Retrieve (S1-012) ---


def test_owner_can_retrieve_their_own_target(client):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(
        f"/api/targets/{target['id']}",
        headers=bearer("token-a"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == target["id"]
    assert response.json()["name"] == "A cafe"
    assert "owner_id" not in response.json()


def test_user_cannot_retrieve_another_users_target(client):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(
        f"/api/targets/{target['id']}",
        headers=bearer("token-b"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"
    assert "A cafe" not in response.text


def test_user_cannot_retrieve_nonexistent_target(client):
    response = client.get(
        "/api/targets/999999",
        headers=bearer("token-a"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"


# --- Update (S1-012) ---


def test_owner_can_update_their_own_target(client, db):
    target = make_target(client, "token-a", "A cafe")

    response = client.patch(
        f"/api/targets/{target['id']}",
        json={"name": "Updated cafe"},
        headers=bearer("token-a"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == target["id"]
    assert response.json()["name"] == "Updated cafe"
    assert response.json()["source_url"] == GOOD_URL

    stored = saved_targets(db)
    assert len(stored) == 1
    assert stored[0].name == "Updated cafe"
    assert stored[0].source_url == GOOD_URL
    assert stored[0].owner_id == user_id(db, "uid-a")


def test_owner_can_update_only_the_source_url(client, db):
    target = make_target(client, "token-a", "A cafe")

    new_url = (
        "https://www.google.com/maps/search/"
        "?api=1&query=Cafe&query_place_id=ChIJExample1"
    )

    response = client.patch(
        f"/api/targets/{target['id']}",
        json={"source_url": new_url},
        headers=bearer("token-a"),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "A cafe"
    assert response.json()["source_url"] == new_url

    stored = saved_targets(db)
    assert stored[0].name == "A cafe"
    assert stored[0].source_url == new_url


def test_user_cannot_modify_another_users_target(client, db):
    target = make_target(client, "token-a", "A cafe")

    before = saved_targets(db)[0]
    original_id = before.id
    original_owner_id = before.owner_id
    original_name = before.name
    original_source_url = before.source_url

    response = client.patch(
        f"/api/targets/{target['id']}",
        json={"name": "Hijacked cafe"},
        headers=bearer("token-b"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"

    # Query the database again after the rejected request.
    after = saved_targets(db)[0]

    assert after.id == original_id
    assert after.owner_id == original_owner_id
    assert after.name == original_name
    assert after.source_url == original_source_url
    assert after.name == "A cafe"
    assert after.name != "Hijacked cafe"


@pytest.mark.parametrize(
    "headers",
    [{}, bearer("forged-token"), {"Authorization": "Basic abc"}],
)
def test_unauthenticated_user_cannot_update_target(client, db, headers):
    target = make_target(client, "token-a", "A cafe")
    before = saved_targets(db)[0]

    response = client.patch(
        f"/api/targets/{target['id']}",
        json={"name": "Unauthorized change"},
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"

    after = saved_targets(db)[0]
    assert after.name == before.name
    assert after.source_url == before.source_url
    assert after.owner_id == before.owner_id


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "   "},
        {"name": "x" * 256},
        {"source_url": "not a url"},
        {"source_url": "https://example.com/maps/place/x"},
        {"name": None},
        {"source_url": None},
    ],
)
def test_invalid_target_update_is_rejected_without_modification(client, db, payload):
    target = make_target(client, "token-a", "A cafe")
    before = saved_targets(db)[0]

    response = client.patch(
        f"/api/targets/{target['id']}",
        json=payload,
        headers=bearer("token-a"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"

    after = saved_targets(db)[0]
    assert after.name == before.name
    assert after.source_url == before.source_url
    assert after.owner_id == before.owner_id


def test_target_update_ignores_client_supplied_owner_and_platform(client, db):
    target = make_target(client, "token-a", "A cafe")
    other_user = get_or_create_user(db, USER_B)

    response = client.patch(
        f"/api/targets/{target['id']}",
        json={
            "name": "Updated cafe",
            "owner_id": other_user.id,
            "user_id": other_user.id,
            "platform": "yelp",
        },
        headers=bearer("token-a"),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated cafe"
    assert response.json()["platform"] == PLATFORM_GOOGLE_MAPS

    stored = saved_targets(db)
    assert len(stored) == 1
    assert stored[0].name == "Updated cafe"
    assert stored[0].owner_id == user_id(db, "uid-a")
    assert stored[0].owner_id != other_user.id
    assert stored[0].platform == PLATFORM_GOOGLE_MAPS


def test_user_cannot_update_nonexistent_target(client):
    response = client.patch(
        "/api/targets/999999",
        json={"name": "New name"},
        headers=bearer("token-a"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"


def test_update_database_failure_returns_safe_error_and_rolls_back(
    client, db, monkeypatch
):
    target = make_target(client, "token-a", "A cafe")

    def fail(*args, **kwargs):
        raise OperationalError(
            "UPDATE secret-sql",
            {},
            Exception("db host down"),
        )

    monkeypatch.setattr(
        targets_router,
        "update_target_for_owner",
        fail,
    )

    response = client.patch(
        f"/api/targets/{target['id']}",
        json={"name": "Changed cafe"},
        headers=bearer("token-a"),
    )

    assert response.status_code == 500
    assert response.json()["code"] == "unexpected"
    assert "secret-sql" not in response.text
    assert "db host down" not in response.text

    stored = saved_targets(db)
    assert len(stored) == 1
    assert stored[0].name == "A cafe"
    assert stored[0].owner_id == user_id(db, "uid-a")
