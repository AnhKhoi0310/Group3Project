import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.adapters.review_source import fetch_reviews_from_url
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_session
from app.errors import ApiError
from app.models import User
from app.repositories.targets import get_target_for_owner
from app.services.ingestion import IngestionError, collect_reviews

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/targets")

PROVIDER_MAX_REVIEWS = 50

INGESTION_ERRORS: dict[str, tuple[int, str]] = {
    "invalid_source": (
        422,
        "That Google Maps link can't be used to collect reviews. "
        "Check the link and try again.",
    ),
    "provider_timeout": (
        504,
        "The review source took too long to respond. Try again in a few minutes.",
    ),
    "provider_quota": (
        429,
        "We've reached our review collection limit for now. Please try again later.",
    ),
    "provider_unavailable": (
        502,
        "We couldn't reach the review source. Try again in a few minutes.",
    ),
    "unexpected": (
        502,
        "We couldn't collect reviews this time. Please try again later.",
    ),
}


class IngestionRead(BaseModel):
    target_id: int
    reviews_found: int
    reviews_skipped: int


def get_review_fetcher() -> Callable[[str], list[dict]]:
    """The review source. Tests replace this so no live provider is called."""

    def fetch(source_url: str) -> list[dict]:
        limit = min(get_settings().ingestion_max_reviews, PROVIDER_MAX_REVIEWS)
        return fetch_reviews_from_url(source_url, limit=limit)

    return fetch


@router.post("/{target_id}/ingestions", response_model=IngestionRead)
def start_ingestion(
    target_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    fetch: Annotated[Callable[[str], list[dict]], Depends(get_review_fetcher)],
) -> IngestionRead:
    # Ownership is checked first, before any provider call or review processing.
    try:
        target = get_target_for_owner(session, target_id, owner_id=user.id)
    except SQLAlchemyError:
        logger.exception("Could not load target %s for user %s", target_id, user.id)
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None
    if target is None:
        # Same response whether it doesn't exist or belongs to someone else.
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "target_not_found",
            "We couldn't find that target. It may not exist or you may not "
            "have access.",
        )

    # The source URL always comes from the stored target, never from the request.
    try:
        outcome = collect_reviews(target.id, target.source_url, fetch)
    except IngestionError as exc:
        logger.warning(
            "Ingestion failed for target %s (%s)",
            target.id,
            exc.category,
            exc_info=True,
        )
        status_code, message = INGESTION_ERRORS.get(
            exc.category, INGESTION_ERRORS["unexpected"]
        )
        raise ApiError(status_code, f"ingestion_{exc.category}", message) from None

    return IngestionRead(
        target_id=target.id,
        reviews_found=outcome.reviews_found,
        reviews_skipped=outcome.reviews_skipped,
    )
