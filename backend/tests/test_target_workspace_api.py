"""GET /api/targets/{id} against real MySQL. Needs TEST_DATABASE_URL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.adapters.identity import InvalidTokenError, VerifiedIdentity
from app.auth import get_token_verifier
from app.db import get_session
from app.main import app
from app.models import PLATFORM_GOOGLE_MAPS, AnalysisTarget, Review
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


def test_owner_can_get_review_summary_from_persisted_reviews(client, db):
    target = make_target(client, "token-a", "A cafe")
    db.add_all(
        [
            Review(
                target_id=target["id"],
                source_platform=PLATFORM_GOOGLE_MAPS,
                rating=5.0,
                text="Great espresso!",
            ),
            Review(
                target_id=target["id"],
                source_platform=PLATFORM_GOOGLE_MAPS,
                rating=4.0,
                text="Friendly staff.",
            ),
            Review(
                target_id=target["id"],
                source_platform=PLATFORM_GOOGLE_MAPS,
                rating=3.0,
                text="Good but slow.",
            ),
        ]
    )
    db.commit()

    response = client.get(
        f"/api/targets/{target['id']}/summary", headers=bearer("token-a")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_id"] == target["id"]
    assert body["target_name"] == "A cafe"
    assert body["review_count"] == 3
    assert body["average_rating"] == 4.0
    assert body["rating_distribution"] == {
        "1": 0,
        "2": 0,
        "3": 1,
        "4": 1,
        "5": 1,
    }


def test_empty_target_summary_returns_zero_count_and_null_average(client, db):
    target = make_target(client, "token-a", "Empty cafe")

    response = client.get(
        f"/api/targets/{target['id']}/summary", headers=bearer("token-a")
    )

    assert response.status_code == 200
    assert response.json() == {
        "target_id": target["id"],
        "target_name": "Empty cafe",
        "review_count": 0,
        "average_rating": None,
        "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
    }


def test_another_users_target_summary_is_denied(client, db):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(
        f"/api/targets/{target['id']}/summary", headers=bearer("token-b")
    )

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"
    assert "A cafe" not in response.text


def test_unauthenticated_target_summary_is_rejected(client, db):
    target = make_target(client, "token-a", "A cafe")

    response = client.get(f"/api/targets/{target['id']}/summary")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_summary_updates_when_persisted_reviews_are_added_or_removed(client, db):
    target = make_target(client, "token-a", "Dynamic cafe")
    first = Review(
        target_id=target["id"],
        source_platform=PLATFORM_GOOGLE_MAPS,
        rating=5.0,
        text="Amazing coffee!",
    )
    second = Review(
        target_id=target["id"],
        source_platform=PLATFORM_GOOGLE_MAPS,
        rating=3.0,
        text="Average pastry.",
    )
    db.add_all([first, second])
    db.commit()

    initial = client.get(
        f"/api/targets/{target['id']}/summary", headers=bearer("token-a")
    )
    assert initial.status_code == 200
    assert initial.json()["review_count"] == 2
    assert initial.json()["average_rating"] == 4.0

    # Add a third persisted review -> count and average update dynamically.
    third = Review(
        target_id=target["id"],
        source_platform=PLATFORM_GOOGLE_MAPS,
        rating=1.0,
        text="Cold espresso.",
    )
    db.add(third)
    db.commit()

    after_add = client.get(
        f"/api/targets/{target['id']}/summary", headers=bearer("token-a")
    )
    assert after_add.status_code == 200
    assert after_add.json()["review_count"] == 3
    assert after_add.json()["average_rating"] == 3.0
    assert after_add.json()["rating_distribution"] == {
        "1": 1,
        "2": 0,
        "3": 1,
        "4": 0,
        "5": 1,
    }

    # Remove a persisted review -> summary reflects only remaining active rows.
    db.delete(third)
    db.commit()

    after_remove = client.get(
        f"/api/targets/{target['id']}/summary", headers=bearer("token-a")
    )
    assert after_remove.status_code == 200
    assert after_remove.json()["review_count"] == 2
    assert after_remove.json()["average_rating"] == 4.0
    assert after_remove.json()["rating_distribution"] == {
        "1": 0,
        "2": 0,
        "3": 1,
        "4": 0,
        "5": 1,
    }


def test_summaries_are_isolated_per_target_for_same_owner(client, db):
    target_a = make_target(client, "token-a", "Target A Cafe")
    target_b = make_target(client, "token-a", "Target B Bakery")
    db.add_all(
        [
            Review(
                target_id=target_a["id"],
                source_platform=PLATFORM_GOOGLE_MAPS,
                rating=5.0,
                text="Best latte in town.",
            ),
            Review(
                target_id=target_b["id"],
                source_platform=PLATFORM_GOOGLE_MAPS,
                rating=2.0,
                text="Stale bread.",
            ),
            Review(
                target_id=target_b["id"],
                source_platform=PLATFORM_GOOGLE_MAPS,
                rating=2.0,
                text="Slow line.",
            ),
        ]
    )
    db.commit()

    res_a = client.get(
        f"/api/targets/{target_a['id']}/summary", headers=bearer("token-a")
    )
    res_b = client.get(
        f"/api/targets/{target_b['id']}/summary", headers=bearer("token-a")
    )

    assert res_a.status_code == 200
    assert res_a.json() == {
        "target_id": target_a["id"],
        "target_name": "Target A Cafe",
        "review_count": 1,
        "average_rating": 5.0,
        "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 1},
    }

    assert res_b.status_code == 200
    assert res_b.json() == {
        "target_id": target_b["id"],
        "target_name": "Target B Bakery",
        "review_count": 2,
        "average_rating": 2.0,
        "rating_distribution": {"1": 0, "2": 2, "3": 0, "4": 0, "5": 0},
    }


def test_cross_user_summary_isolation_with_populated_reviews(client, db):
    target_a = make_target(client, "token-a", "Secret Cafe")
    db.add(
        Review(
            target_id=target_a["id"],
            source_platform=PLATFORM_GOOGLE_MAPS,
            rating=5.0,
            text="Confidential review.",
        )
    )
    db.commit()

    response = client.get(
        f"/api/targets/{target_a['id']}/summary", headers=bearer("token-b")
    )

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"
    assert "Secret Cafe" not in response.text
