
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.errors import ApiError
from app.models import User
from app.repositories.targets import get_owned_target

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("/{target_id}")
def read_target(
    target_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    target = get_owned_target(session, target_id, user)

    if target is None:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "target_not_found",
            "We couldn't find that target.",
        )

    return {
        "id": target.id,
        "name": target.name,
        "platform": target.platform,
        "source_url": target.source_url,
        "created_at": target.created_at.isoformat(),
    }
    
