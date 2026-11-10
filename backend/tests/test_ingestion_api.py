"""POST /api/targets/{id}/ingestions against real MySQL. Needs TEST_DATABASE_URL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.adapters.identity import InvalidTokenError, VerifiedIdentity
from app.adapters.review_source import ReviewSourceError
from app.auth import get_token_verifier
from app.db import get_session
from app.main import app
from app.routers import ingestions as ingestions_router
from app.routers.ingestions import get_review_fetcher

USER_A = VerifiedIdentity(uid="uid-a", email="a@example.com")
USER_B = VerifiedIdentity(uid="uid-b", email="b@example.com")
GOOD_URL = "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2"
GOOD_REVIEW = {"review_id": "r1", "rating": 5, "snippet": "Great coffee"}


class FakeVerifier:
    tokens = {"token-a": USER_A, "token-b": USER_B}

    def verify(self, token):
        if token not in self.tokens:
            raise InvalidTokenError
        return self.tokens[token]

    def revoke(self, uid):
        pass


class FakeFetcher:
    """Stands in for the review provider. Records every call."""

    def __init__(self):
        self.calls = []
        self.result = []
        self.error = None

    def __call__(self, source_url):
        self.calls.append(source_url)
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def fetcher():
    return FakeFetcher()


@pytest.fixture
def client(db, session_factory, fetcher):
    def session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_token_verifier] = lambda: FakeVerifier()
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_review_fetcher] = lambda: fetcher
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


def ingest(client, target_id, token="token-a", **kwargs):
    return client.post(
        f"/api/targets/{target_id}/ingestions", headers=bearer(token), **kwargs
    )


def test_owner_can_start_ingestion_from_the_stored_source_url(client, fetcher):
    target = make_target(client, "token-a", "A cafe")
    fetcher.result = [GOOD_REVIEW]

    response = ingest(client, target["id"])

    assert response.status_code == 200
    assert response.json() == {
        "target_id": target["id"],
        "reviews_found": 1,
        "reviews_skipped": 0,
    }
    assert fetcher.calls == [GOOD_URL]


def test_client_supplied_source_and_owner_are_ignored(client, fetcher):
    target = make_target(client, "token-a", "A cafe")

    response = ingest(
        client,
        target["id"],
        json={"source_url": "https://evil.example/", "owner_id": 999},
    )

    assert response.status_code == 200
    assert fetcher.calls == [GOOD_URL]


def test_another_users_target_is_denied_before_any_processing(client, fetcher):
    target = make_target(client, "token-a", "A cafe")

    response = ingest(client, target["id"], token="token-b")

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"
    assert "A cafe" not in response.text
    assert GOOD_URL not in response.text
    assert fetcher.calls == []


def test_missing_and_foreign_targets_get_identical_responses(client, fetcher):
    target = make_target(client, "token-a", "A cafe")

    foreign = ingest(client, target["id"], token="token-b")
    missing = ingest(client, 999999, token="token-b")

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    assert fetcher.calls == []


@pytest.mark.parametrize(
    "headers", [{}, bearer("forged-token"), {"Authorization": "Basic abc"}]
)
def test_unauthenticated_ingestion_is_rejected_without_processing(
    client, fetcher, headers
):
    target = make_target(client, "token-a", "A cafe")

    response = client.post(f"/api/targets/{target['id']}/ingestions", headers=headers)

    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert "A cafe" not in response.text
    assert fetcher.calls == []


def test_reviews_without_text_or_rating_are_skipped_not_counted(client, fetcher):
    target = make_target(client, "token-a", "A cafe")
    fetcher.result = [
        GOOD_REVIEW,
        {"review_id": "r2", "rating": 4},
        {"review_id": "r3", "snippet": "No rating"},
    ]

    body = ingest(client, target["id"]).json()

    assert body["reviews_found"] == 1
    assert body["reviews_skipped"] == 2


def test_an_empty_provider_result_reports_zero_and_invents_nothing(client, fetcher):
    target = make_target(client, "token-a", "A cafe")
    fetcher.result = []

    body = ingest(client, target["id"]).json()

    assert body["reviews_found"] == 0
    assert body["reviews_skipped"] == 0


@pytest.mark.parametrize(
    ("category", "status_code"),
    [
        ("invalid_source", 422),
        ("provider_timeout", 504),
        ("provider_quota", 429),
        ("provider_unavailable", 502),
        ("unexpected", 502),
    ],
)
def test_provider_failures_are_distinct_and_never_leak_details(
    client, fetcher, category, status_code
):
    target = make_target(client, "token-a", "A cafe")
    fetcher.error = ReviewSourceError(category, "secret-provider-details")

    response = ingest(client, target["id"])

    assert response.status_code == status_code
    assert response.json()["code"] == f"ingestion_{category}"
    assert "secret-provider-details" not in response.text
    assert "Traceback" not in response.text


def test_malformed_provider_data_fails_cleanly(client, fetcher):
    target = make_target(client, "token-a", "A cafe")
    fetcher.result = [{"rating": 9, "snippet": "Impossible rating"}]

    response = ingest(client, target["id"])

    assert response.status_code == 502
    assert response.json()["code"] == "ingestion_unexpected"


def test_database_failure_returns_a_safe_error_and_skips_the_provider(
    client, fetcher, monkeypatch
):
    def fail(*args, **kwargs):
        raise OperationalError("SELECT secret-sql", {}, Exception("db host down"))

    monkeypatch.setattr(ingestions_router, "get_target_for_owner", fail)

    response = ingest(client, 1)

    assert response.status_code == 500
    assert response.json()["code"] == "unexpected"
    assert "secret-sql" not in response.text
    assert "db host down" not in response.text
    assert fetcher.calls == []
