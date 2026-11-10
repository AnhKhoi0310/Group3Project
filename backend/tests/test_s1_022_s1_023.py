"""Integration coverage for persisted reviews and ingestion attempt reporting."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.adapters.identity import InvalidTokenError, VerifiedIdentity
from app.adapters.review_source import ReviewSourceError
from app.auth import get_token_verifier
from app.config import load_settings
from app.db import get_session
from app.main import app
from app.models import IngestionAttempt, Review
from app.routers.ingestions import get_review_fetcher

USER_A = VerifiedIdentity(uid="s1-022-user-a", email="a@example.com")
USER_B = VerifiedIdentity(uid="s1-022-user-b", email="b@example.com")
SOURCE_URL = "https://www.google.com/maps/place/Test/data=!1s0x1:0x2"


class FakeVerifier:
    """Test-only Firebase token verifier."""

    def verify(self, token):
        identities = {"token-a": USER_A, "token-b": USER_B}
        if token not in identities:
            raise InvalidTokenError
        return identities[token]

    def revoke(self, uid):
        return None


class FakeFetcher:
    """Deterministic review provider used by the integration tests."""

    def __init__(self):
        self.reviews = []
        self.error = None

    def __call__(self, source_url):
        assert source_url == SOURCE_URL
        if self.error:
            raise self.error
        return self.reviews


@pytest.fixture
def fetcher():
    return FakeFetcher()


@pytest.fixture
def client(session_factory, fetcher, monkeypatch):
    def session_override():
        with session_factory() as session:
            yield session

    fake_verifier = FakeVerifier()

    # The app lifespan calls get_settings() directly during startup.
    # Mock settings so CI does not require real environment secrets.
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: load_settings(
            database_url="sqlite:///unused.db",
            firebase_project_id="test-project",
            firebase_credentials_path="unused.json",
            review_provider_api_key="test-api-key",
        ),
    )

    # The app lifespan calls get_token_verifier() directly during startup.
    # A FastAPI dependency override does not intercept that direct call.
    monkeypatch.setattr(
        main_module,
        "get_token_verifier",
        lambda: fake_verifier,
    )

    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_token_verifier] = lambda: fake_verifier
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_review_fetcher] = lambda: fetcher

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture(autouse=True)
def clear_database(db):
    # The shared db fixture clears all user-scoped test tables for each test.
    yield


def headers(token="token-a"):
    return {"Authorization": f"Bearer {token}"}


def create_target(client, name="Test business", token="token-a"):
    response = client.post(
        "/api/targets",
        json={"name": name, "source_url": SOURCE_URL},
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def start(client, target_id, token="token-a"):
    return client.post(
        f"/api/targets/{target_id}/ingestions",
        headers=headers(token),
    )


def latest(client, target_id, token="token-a"):
    return client.get(
        f"/api/targets/{target_id}/ingestions/latest",
        headers=headers(token),
    )


def test_s1_022_ingestion_persists_normalized_reviews_for_the_correct_target(
    client, fetcher, session_factory
):
    target_a = create_target(client, "Target A")
    target_b = create_target(client, "Target B")
    fetcher.reviews = [
        {
            "review_id": "source-review-1",
            "rating": 5,
            "snippet": "Excellent service.",
            "user": {"name": "Reviewer One"},
            "date": "2 weeks ago",
        },
        {
            "review_id": "source-review-2",
            "rating": 3,
            "snippet": "Average experience.",
        },
        # Missing required text: it must be skipped, not fabricated or saved.
        {"review_id": "source-review-3", "rating": 4},
    ]

    response = start(client, target_a["id"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "succeeded"
    assert response.json()["reviews_found"] == 2
    assert response.json()["reviews_skipped"] == 1

    with session_factory() as session:
        target_a_reviews = session.scalars(
            select(Review).where(Review.target_id == target_a["id"])
        ).all()
        target_b_reviews = session.scalars(
            select(Review).where(Review.target_id == target_b["id"])
        ).all()

        assert len(target_a_reviews) == 2
        assert target_b_reviews == []

        by_source_id = {review.source_review_id: review for review in target_a_reviews}
        first = by_source_id["source-review-1"]

        assert first.text == "Excellent service."
        assert first.rating == 5
        assert first.reviewer_name == "Reviewer One"
        assert first.review_date == "2 weeks ago"
        assert first.source_platform == target_a["platform"]
        assert first.target_id == target_a["id"]

    listed = client.get(
        f"/api/targets/{target_a['id']}/reviews",
        headers=headers(),
    )
    assert listed.status_code == 200
    assert {item["source_review_id"] for item in listed.json()} == {
        "source-review-1",
        "source-review-2",
    }


def test_s1_022_reingestion_does_not_duplicate_source_review_ids(
    client, fetcher, session_factory
):
    target = create_target(client)
    fetcher.reviews = [
        {
            "review_id": "same-id",
            "rating": 5,
            "snippet": "Real review.",
        }
    ]

    first = start(client, target["id"])
    second = start(client, target["id"])

    assert first.status_code == second.status_code == 200

    with session_factory() as session:
        saved = session.scalars(
            select(Review).where(Review.target_id == target["id"])
        ).all()
        assert len(saved) == 1


def test_s1_023_successful_attempt_is_persisted_and_readable_after_reload(
    client, fetcher, session_factory
):
    target = create_target(client)
    fetcher.reviews = [
        {
            "review_id": "success-1",
            "rating": 5,
            "snippet": "A genuine review.",
        }
    ]

    started = start(client, target["id"])
    assert started.status_code == 200

    body = started.json()
    assert body["status"] == "succeeded"
    assert body["completed_at"] is not None

    response = latest(client, target["id"])
    assert response.status_code == 200
    assert response.json()["attempt_id"] == body["attempt_id"]
    assert response.json()["status"] == "succeeded"
    assert response.json()["reviews_found"] == 1

    with session_factory() as session:
        attempts = session.scalars(
            select(IngestionAttempt).where(IngestionAttempt.target_id == target["id"])
        ).all()

        assert len(attempts) == 1
        assert attempts[0].status == "succeeded"


def test_s1_023_provider_failure_is_recorded_and_existing_reviews_are_retained(
    client, fetcher, session_factory
):
    target = create_target(client)
    fetcher.reviews = [
        {
            "review_id": "kept-review",
            "rating": 4,
            "snippet": "Keep this review.",
        }
    ]

    first = start(client, target["id"])
    assert first.status_code == 200

    fetcher.error = ReviewSourceError(
        "provider_unavailable",
        "private provider diagnostics",
    )

    failed = start(client, target["id"])
    assert failed.status_code == 502
    assert "private provider diagnostics" not in failed.text

    latest_response = latest(client, target["id"])
    assert latest_response.status_code == 200
    assert latest_response.json()["status"] == "failed"
    assert latest_response.json()["completed_at"] is not None

    with session_factory() as session:
        reviews = session.scalars(
            select(Review).where(Review.target_id == target["id"])
        ).all()

        attempts = session.scalars(
            select(IngestionAttempt)
            .where(IngestionAttempt.target_id == target["id"])
            .order_by(IngestionAttempt.id)
        ).all()

        assert len(reviews) == 1
        assert reviews[0].source_review_id == "kept-review"
        assert [attempt.status for attempt in attempts] == [
            "succeeded",
            "failed",
        ]
        assert attempts[-1].failure_category == "provider_unavailable"


def test_s1_023_foreign_user_cannot_read_ingestion_history(client, fetcher):
    target = create_target(client)
    fetcher.reviews = [
        {
            "review_id": "private",
            "rating": 5,
            "snippet": "Private review.",
        }
    ]

    assert start(client, target["id"]).status_code == 200

    foreign = latest(client, target["id"], token="token-b")
    missing = latest(client, 999999, token="token-b")

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
