from pathlib import Path

import pytest
from firebase_admin import auth
from firebase_admin.exceptions import UNAVAILABLE, FirebaseError

from app.adapters import identity
from app.adapters.identity import (
    FirebaseTokenVerifier,
    IdentityServiceError,
    InvalidTokenError,
)
from app.config import ConfigurationError


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.setattr(identity.credentials, "Certificate", lambda path: object())
    monkeypatch.setattr(
        identity.firebase_admin, "initialize_app", lambda *args: "firebase-app"
    )
    return FirebaseTokenVerifier(Path("key.json"), "demo")


def fail_with(monkeypatch, name, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(identity.auth, name, fail)


def test_verify_checks_revocation_and_returns_identity(verifier, monkeypatch):
    calls = {}

    def fake_verify(token, app, check_revoked, clock_skew_seconds):
        calls.update(
            token=token,
            app=app,
            check_revoked=check_revoked,
            clock_skew_seconds=clock_skew_seconds,
        )
        return {"uid": "uid-a", "email": "a@example.com"}

    monkeypatch.setattr(identity.auth, "verify_id_token", fake_verify)

    result = verifier.verify("token")

    assert (result.uid, result.email) == ("uid-a", "a@example.com")
    assert calls == {
        "token": "token",
        "app": "firebase-app",
        "check_revoked": True,
        "clock_skew_seconds": 5,
    }


def test_verify_allows_identity_without_email(verifier, monkeypatch):
    monkeypatch.setattr(
        identity.auth, "verify_id_token", lambda *a, **k: {"uid": "uid-a"}
    )

    assert verifier.verify("token").email is None


@pytest.mark.parametrize(
    "error",
    [
        ValueError("empty"),
        auth.InvalidIdTokenError("bad"),
        auth.ExpiredIdTokenError("expired", None),
        auth.RevokedIdTokenError("revoked"),
        auth.UserDisabledError("disabled"),
        auth.UserNotFoundError("gone"),
    ],
)
def test_unusable_tokens_are_invalid(verifier, monkeypatch, error):
    fail_with(monkeypatch, "verify_id_token", error)

    with pytest.raises(InvalidTokenError):
        verifier.verify("token")


@pytest.mark.parametrize(
    "error",
    [auth.CertificateFetchError("down", None), FirebaseError(UNAVAILABLE, "down")],
)
def test_provider_failure_is_not_reported_as_bad_token(verifier, monkeypatch, error):
    fail_with(monkeypatch, "verify_id_token", error)

    with pytest.raises(IdentityServiceError):
        verifier.verify("token")


def test_revoke_failure_is_reported(verifier, monkeypatch):
    fail_with(monkeypatch, "revoke_refresh_tokens", FirebaseError(UNAVAILABLE, "down"))

    with pytest.raises(IdentityServiceError):
        verifier.revoke("uid-a")


@pytest.mark.parametrize("error", [FileNotFoundError("nope"), ValueError("bad key")])
def test_unusable_key_file_names_the_setting(monkeypatch, error):
    def fail(path):
        raise error

    monkeypatch.setattr(identity.credentials, "Certificate", fail)

    with pytest.raises(ConfigurationError, match="FIREBASE_CREDENTIALS_PATH"):
        FirebaseTokenVerifier(Path("missing.json"), "demo")
