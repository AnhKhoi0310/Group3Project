import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.adapters.identity import (
    IdentityServiceError,
    TokenVerifier,
    VerifiedIdentity,
)
from app.auth import get_current_user, get_token_verifier, identity_unavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

CurrentUser = Annotated[VerifiedIdentity, Depends(get_current_user)]


@router.get("/me")
def read_current_user(user: CurrentUser) -> dict[str, str | None]:
    return {"uid": user.uid, "email": user.email}


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: CurrentUser,
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> None:
    try:
        verifier.revoke(user.uid)
    except IdentityServiceError:
        logger.exception("Could not revoke tokens for uid %s", user.uid)
        raise identity_unavailable() from None
