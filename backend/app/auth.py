import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.adapters.identity import (
    FirebaseTokenVerifier,
    IdentityServiceError,
    InvalidTokenError,
    TokenVerifier,
    VerifiedIdentity,
)
from app.config import get_settings
from app.db import get_session
from app.errors import ApiError
from app.models import User
from app.repositories.users import get_or_create_user

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def unauthenticated() -> ApiError:
    return ApiError(
        status.HTTP_401_UNAUTHORIZED,
        "unauthenticated",
        "Please log in to continue.",
    )


def identity_unavailable() -> ApiError:
    return ApiError(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "auth_unavailable",
        "We couldn't confirm your sign-in right now. Please try again shortly.",
    )


@lru_cache
def get_token_verifier() -> TokenVerifier:
    settings = get_settings()
    return FirebaseTokenVerifier(
        settings.firebase_credentials_file, settings.firebase_project_id
    )


def get_verified_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> VerifiedIdentity:
    """Return the identity proven by the bearer token."""
    if credentials is None:
        raise unauthenticated()
    try:
        return verifier.verify(credentials.credentials)
    except InvalidTokenError:
        raise unauthenticated() from None
    except IdentityServiceError:
        logger.exception("Could not verify token with the identity provider")
        raise identity_unavailable() from None


def get_current_user(
    identity: Annotated[VerifiedIdentity, Depends(get_verified_identity)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Return the owner for this request. This is the only source of user identity."""
    try:
        return get_or_create_user(session, identity)
    except SQLAlchemyError:
        logger.exception("Could not load the user for uid %s", identity.uid)
        raise ApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_unavailable",
            "We couldn't load your account right now. Please try again shortly.",
        ) from None
