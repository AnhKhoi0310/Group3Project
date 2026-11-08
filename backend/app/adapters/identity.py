"""Boundary around the managed identity provider (Firebase Authentication)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError

from app.config import ConfigurationError

TOKEN_CLOCK_SKEW_SECONDS = 5


@dataclass(frozen=True)
class VerifiedIdentity:
    uid: str
    email: str | None


class InvalidTokenError(Exception):
    """The token is malformed, expired, revoked, or its user is unusable."""


class IdentityServiceError(Exception):
    """The provider could not be reached, so the token could not be checked."""


class TokenVerifier(Protocol):
    def verify(self, token: str) -> VerifiedIdentity: ...

    def revoke(self, uid: str) -> None: ...


class FirebaseTokenVerifier:
    def __init__(self, credentials_path: Path, project_id: str) -> None:
        try:
            credential = credentials.Certificate(str(credentials_path))
        except (OSError, ValueError):
            raise ConfigurationError(
                "ReviewLens cannot start: FIREBASE_CREDENTIALS_PATH does not point "
                "to a valid Firebase service account key file."
            ) from None
        self._app = firebase_admin.initialize_app(credential, {"projectId": project_id})

    def verify(self, token: str) -> VerifiedIdentity:
        try:
            # check_revoked makes tokens stop working after logout (S1-BR-006).
            # A small skew stops brand-new tokens failing as "used too early".
            claims = auth.verify_id_token(
                token,
                app=self._app,
                check_revoked=True,
                clock_skew_seconds=TOKEN_CLOCK_SKEW_SECONDS,
            )
        except (
            ValueError,
            auth.InvalidIdTokenError,
            auth.UserDisabledError,
            auth.UserNotFoundError,
        ) as exc:
            raise InvalidTokenError from exc
        except FirebaseError as exc:
            raise IdentityServiceError from exc
        return VerifiedIdentity(uid=claims["uid"], email=claims.get("email"))

    def revoke(self, uid: str) -> None:
        try:
            auth.revoke_refresh_tokens(uid, app=self._app)
        except FirebaseError as exc:
            raise IdentityServiceError from exc
