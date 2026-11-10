
from typing import Annotated
import logging

from app.adapters.review_source import ReviewSourceError, fetch_reviews_from_url

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.errors import ApiError
from app.models import User
from app.repositories.targets import get_owned_target

router = APIRouter(prefix="/api/targets", tags=["targets"])
logger = logging.getLogger(__name__)

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


@router.post("/{target_id}/ingestions")
def start_ingestion(
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

    if not target.source_url or not target.source_url.strip():
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "invalid_source",
            "This target needs a Google Maps source URL.",
        )

    try:
        reviews = fetch_reviews_from_url(target.source_url)

    except ReviewSourceError as exc:
        logger.warning(
            "Review ingestion failed for target %s: %s",
            target.id,
            exc.category,
        )
        raise ApiError(
            status.HTTP_502_BAD_GATEWAY,
            exc.category,
            "We couldn't collect reviews. Please check the source or try again.",
        ) from None

    return {
        "target_id": target.id,
        "fetched_count": len(reviews),
        "message": "Review collection completed.",
    }

