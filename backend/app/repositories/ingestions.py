from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IngestionAttempt


def create_attempt(session: Session, target_id: int) -> IngestionAttempt:
    """Persist a processing attempt before calling the external provider."""
    attempt = IngestionAttempt(
        target_id=target_id,
        status="processing",
        reviews_found=0,
        reviews_skipped=0,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def get_latest_attempt_for_target(
    session: Session,
    target_id: int,
) -> IngestionAttempt | None:
    """Return the newest attempt for one target.

    The caller must authorize ownership of the target before calling this
    function. Ordering by id breaks ties when timestamps have equal precision.
    """
    statement = (
        select(IngestionAttempt)
        .where(IngestionAttempt.target_id == target_id)
        .order_by(IngestionAttempt.started_at.desc(), IngestionAttempt.id.desc())
        .limit(1)
    )
    return session.scalars(statement).one_or_none()


def complete_attempt(
    session: Session,
    attempt: IngestionAttempt,
    reviews_found: int,
    reviews_skipped: int,
) -> IngestionAttempt:
    """Commit pending Review inserts and the successful attempt atomically."""
    attempt.status = "succeeded"
    attempt.reviews_found = reviews_found
    attempt.reviews_skipped = reviews_skipped
    attempt.failure_category = None
    attempt.completed_at = datetime.now(UTC)

    # save_reviews() adds Review rows to this same session. This commit makes
    # those rows and the succeeded attempt visible together.
    session.commit()
    session.refresh(attempt)
    return attempt


def fail_attempt(
    session: Session,
    attempt: IngestionAttempt,
    failure_category: str,
) -> IngestionAttempt:
    """Persist a failed attempt without changing previously saved reviews."""
    attempt.status = "failed"
    attempt.failure_category = failure_category
    attempt.completed_at = datetime.now(UTC)

    session.commit()
    session.refresh(attempt)
    return attempt
