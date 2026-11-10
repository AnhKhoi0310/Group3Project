from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Review


def create_review(
    session: Session,
    target_id: int,
    source_platform: str,
    text: str,
    rating: float,
) -> Review:
    """Create a review for a target that the caller has already authorized."""
    review = Review(
        target_id=target_id,
        source_platform=source_platform,
        text=text,
        rating=rating,
    )

    session.add(review)
    session.commit()
    session.refresh(review)

    return review


def save_reviews(
    session: Session,
    target_id: int,
    source_platform: str,
    reviews: list[dict],
) -> int:
    """Save usable reviews, avoiding re-inserting known source review IDs.

    Ownership is inherited from target_id. Callers must verify that the
    authenticated user owns the target before calling this repository.
    """
    source_ids = {
        review["review_id"] for review in reviews if review.get("review_id") is not None
    }

    existing_ids: set[str] = set()
    if source_ids:
        query = select(Review.source_review_id).where(
            Review.target_id == target_id,
            Review.source_review_id.in_(source_ids),
        )
        existing_ids = set(session.scalars(query).all())

    saved = 0
    for item in reviews:
        source_id = item.get("review_id")
        if source_id is not None and source_id in existing_ids:
            continue

        session.add(
            Review(
                target_id=target_id,
                source_review_id=source_id,
                source_platform=source_platform,
                reviewer_name=item.get("author"),
                rating=item["rating"],
                text=item["text"],
                review_date=item.get("date"),
            )
        )
        if source_id is not None:
            existing_ids.add(source_id)
        saved += 1

    return saved


def list_reviews_for_target(session: Session, target_id: int) -> list[Review]:
    """Return reviews belonging to one already-authorized target."""
    query = (
        select(Review)
        .where(Review.target_id == target_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    )
    return list(session.scalars(query).all())
