from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IngestionAttempt


def create_attempt(session: Session, target_id: int) -> IngestionAttempt:
    """Create and persist a new ingestion attempt in processing state."""
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


def get_attempt(session: Session, attempt_id: int) -> IngestionAttempt | None:
    """Retrieve an ingestion attempt by its ID."""
    return session.scalars(
        select(IngestionAttempt).where(IngestionAttempt.id == attempt_id)
    ).one_or_none()


def complete_attempt(
    session: Session,
    attempt: IngestionAttempt,
    reviews_found: int,
    reviews_skipped: int,
) -> IngestionAttempt:
    """Mark an ingestion attempt as successful and record its results."""
    attempt.status = "succeeded"
    attempt.reviews_found = reviews_found
    attempt.reviews_skipped = reviews_skipped
    attempt.failure_category = None
    attempt.completed_at = datetime.now(UTC)

    session.commit()
    session.refresh(attempt)
    return attempt


def fail_attempt(
    session: Session,
    attempt: IngestionAttempt,
    failure_category: str,
) -> IngestionAttempt:
    """Mark an ingestion attempt as failed and record its failure category."""
    attempt.status = "failed"
    attempt.failure_category = failure_category
    attempt.completed_at = datetime.now(UTC)

    session.commit()
    session.refresh(attempt)
    return attempt
