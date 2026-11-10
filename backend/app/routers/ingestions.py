import logging
from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.adapters.review_source import fetch_reviews_from_url
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_session
from app.errors import ApiError
from app.models import IngestionAttempt, User
from app.repositories.ingestions import (
    complete_attempt,
    create_attempt,
    fail_attempt,
)
from app.repositories.reviews import (
    create_review,
    list_reviews_for_target,
    save_reviews,
)
from app.repositories.targets import get_target_for_owner
from app.schemas import ReviewCreate
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
    attempt_id: int
    target_id: int
    status: str
    reviews_found: int
    reviews_skipped: int


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    source_review_id: str | None
    source_platform: str
    reviewer_name: str | None
    rating: float
    text: str
    review_date: str | None
    created_at: datetime


def get_review_fetcher() -> Callable[[str], list[dict]]:
    """The review source. Tests replace this so no live provider is called."""

    def fetch(source_url: str) -> list[dict]:
        limit = min(get_settings().ingestion_max_reviews, PROVIDER_MAX_REVIEWS)
        return fetch_reviews_from_url(source_url, limit=limit)

    return fetch


def _target_not_found() -> ApiError:
    return ApiError(
        status.HTTP_404_NOT_FOUND,
        "target_not_found",
        "We couldn't find that target. It may not exist or you may not have access.",
    )


def _record_failure(
    session: Session,
    attempt: IngestionAttempt,
    category: str,
) -> None:
    try:
        fail_attempt(session, attempt, category)
    except SQLAlchemyError:
        session.rollback()
        logger.exception(
            "Could not record failure for ingestion attempt %s",
            attempt.id,
        )


@router.post("/{target_id}/ingestions", response_model=IngestionRead)
def start_ingestion(
    target_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    fetch: Annotated[Callable[[str], list[dict]], Depends(get_review_fetcher)],
) -> IngestionRead:
    """Collect, normalize, and persist reviews for an owned target."""

    # Verify ownership before creating an attempt or contacting the provider.
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
        raise _target_not_found()

    # Record the attempt before contacting the external provider.
    try:
        attempt = create_attempt(session, target.id)
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Could not create ingestion attempt for target %s", target.id)
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None

    # Always use the source URL stored on the owned target.
    try:
        outcome = collect_reviews(target.source_url, fetch)
    except IngestionError as exc:
        logger.warning(
            "Ingestion failed for target %s (%s)",
            target.id,
            exc.category,
            exc_info=True,
        )

        _record_failure(session, attempt, exc.category)

        status_code, message = INGESTION_ERRORS.get(
            exc.category,
            INGESTION_ERRORS["unexpected"],
        )

        raise ApiError(
            status_code,
            f"ingestion_{exc.category}",
            message,
        ) from None

    # Save reviews and mark the attempt successful.
    try:
        save_reviews(
            session,
            target_id=target.id,
            source_platform=target.platform,
            reviews=outcome.reviews,
        )

        completed = complete_attempt(
            session,
            attempt,
            reviews_found=outcome.reviews_found,
            reviews_skipped=outcome.reviews_skipped,
        )

    except SQLAlchemyError:
        session.rollback()
        logger.exception("Could not persist ingestion for target %s", target.id)

        # Record the failed outcome after rolling back the review transaction.
        try:
            failed_attempt = session.get(IngestionAttempt, attempt.id)

            if failed_attempt is not None:
                fail_attempt(
                    session,
                    failed_attempt,
                    "persistence_error",
                )

        except SQLAlchemyError:
            session.rollback()
            logger.exception(
                "Could not record persistence failure for attempt %s",
                attempt.id,
            )

        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "ingestion_persistence_error",
            "We collected the reviews but couldn't save them. Please try again.",
        ) from None

    return IngestionRead(
        attempt_id=completed.id,
        target_id=target.id,
        status=completed.status,
        reviews_found=completed.reviews_found,
        reviews_skipped=completed.reviews_skipped,
    )


@router.post(
    "/{target_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_target_review(
    target_id: int,
    payload: ReviewCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewRead:
    """Create a review only when the authenticated user owns its parent target."""

    try:
        # Check parent ownership before performing any child-resource operation.
        target = get_target_for_owner(
            session,
            target_id,
            owner_id=user.id,
        )

        if target is None:
            raise _target_not_found()

        # The client cannot choose the target ID or source platform.
        review = create_review(
            session,
            target_id=target.id,
            source_platform=target.platform,
            text=payload.text,
            rating=payload.rating,
        )

        return review

    except ApiError:
        raise

    except SQLAlchemyError:
        session.rollback()
        logger.exception(
            "Could not create review for target %s and user %s",
            target_id,
            user.id,
        )

        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None


@router.get("/{target_id}/reviews", response_model=list[ReviewRead])
def get_target_reviews(
    target_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list:
    """Return reviews only after verifying ownership of their parent target."""

    try:
        target = get_target_for_owner(
            session,
            target_id,
            owner_id=user.id,
        )

        if target is None:
            raise _target_not_found()

        return list_reviews_for_target(session, target.id)

    except ApiError:
        raise

    except SQLAlchemyError:
        logger.exception("Could not load reviews for target %s", target_id)

        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None
