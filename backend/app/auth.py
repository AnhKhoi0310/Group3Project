import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.identity import (
    FirebaseTokenVerifier,
    IdentityServiceError,
    InvalidTokenError,
    TokenVerifier,
    VerifiedIdentity,
)
from app.config import get_settings
from app.errors import ApiError

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


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> VerifiedIdentity:
    """Return the verified caller. This is the only source of user identity."""
    if credentials is None:
        raise unauthenticated()
    try:
        return verifier.verify(credentials.credentials)
    except InvalidTokenError:
        raise unauthenticated() from None
    except IdentityServiceError:
        logger.exception("Could not verify token with the identity provider")
        raise identity_unavailable() from None
