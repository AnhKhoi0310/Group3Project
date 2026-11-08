import pytest
from fastapi.testclient import TestClient

from app.adapters.identity import (
    IdentityServiceError,
    InvalidTokenError,
    VerifiedIdentity,
)
from app.auth import get_token_verifier
from app.main import app

USER_A = VerifiedIdentity(uid="uid-a", email="a@example.com")
UNAUTHENTICATED_BODY = {
    "code": "unauthenticated",
    "message": "Please log in to continue.",
}


class FakeVerifier:
    def __init__(self):
        self.tokens = {"token-a": USER_A}
        self.revoked = []
        self.unavailable = False

    def verify(self, token):
        if self.unavailable:
            raise IdentityServiceError
        if token not in self.tokens:
            raise InvalidTokenError
        return self.tokens[token]

    def revoke(self, uid):
        if self.unavailable:
            raise IdentityServiceError
        self.revoked.append(uid)
        self.tokens = {t: u for t, u in self.tokens.items() if u.uid != uid}


@pytest.fixture
def verifier():
    fake = FakeVerifier()
    app.dependency_overrides[get_token_verifier] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client(verifier):
    return TestClient(app)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_returns_verified_identity(client):
    response = client.get("/api/me", headers=bearer("token-a"))

    assert response.status_code == 200
    assert response.json() == {"uid": "uid-a", "email": "a@example.com"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "token-a"},
        bearer("forged-token"),
    ],
)
def test_missing_or_invalid_token_is_rejected_without_data(client, headers):
    response = client.get("/api/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == UNAUTHENTICATED_BODY


def test_client_cannot_claim_another_identity(client):
    response = client.get(
        "/api/me?uid=uid-b",
        headers={**bearer("token-a"), "X-User-Id": "uid-b"},
    )

    assert response.json()["uid"] == "uid-a"


def test_token_stops_working_after_logout(client, verifier):
    logout = client.post("/api/auth/logout", headers=bearer("token-a"))
    after = client.get("/api/me", headers=bearer("token-a"))

    assert logout.status_code == 204
    assert verifier.revoked == ["uid-a"]
    assert after.status_code == 401


def test_logout_requires_authentication(client, verifier):
    response = client.post("/api/auth/logout")

    assert response.status_code == 401
    assert verifier.revoked == []


def test_provider_outage_denies_access_with_friendly_error(client, verifier):
    verifier.unavailable = True

    response = client.get("/api/me", headers=bearer("token-a"))

    assert response.status_code == 503
    assert response.json()["code"] == "auth_unavailable"
    assert "uid-a" not in response.text
