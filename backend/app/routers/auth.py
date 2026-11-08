import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.adapters.identity import (
    IdentityServiceError,
    TokenVerifier,
    VerifiedIdentity,
)
from app.auth import (
    get_current_user,
    get_token_verifier,
    get_verified_identity,
    identity_unavailable,
)
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/me")
def read_current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str | None]:
    return {"uid": user.firebase_uid, "email": user.email}


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    # Token only, so people can still log out while the database is down.
    identity: Annotated[VerifiedIdentity, Depends(get_verified_identity)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> None:
    try:
        verifier.revoke(identity.uid)
    except IdentityServiceError:
        logger.exception("Could not revoke tokens for uid %s", identity.uid)
        raise identity_unavailable() from None
