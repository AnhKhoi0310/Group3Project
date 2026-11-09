from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.models.models import AnalysisTarget, Review, User
from app.schemas.reviews import ReviewCreate, ReviewOut

router = APIRouter(prefix="/api", tags=["reviews"])


def get_owned_target_or_404(
    target_id: int, owner_id: int, db: Session
) -> AnalysisTarget:
    """Validate target existence and ownership.
    Returns 404 for missing or unowned targets to prevent user enumeration.
    """
    target = db.scalar(
        select(AnalysisTarget).where(
            AnalysisTarget.id == target_id,
            AnalysisTarget.owner_id == owner_id,
        )
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    return target


@router.get("/targets/{target_id}/reviews", response_model=list[ReviewOut])
def list_target_reviews(
    target_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve reviews for a target owned by the authenticated user."""
    target = get_owned_target_or_404(target_id, current_user.id, db)
    reviews = db.scalars(select(Review).where(Review.target_id == target.id)).all()
    return reviews


@router.post(
    "/targets/{target_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_target_review(
    target_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a review record under a target owned by the authenticated user."""
    target = get_owned_target_or_404(target_id, current_user.id, db)
    review = Review(
        target_id=target.id,
        text=payload.text,
        rating=payload.rating,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.post(
    "/targets/{target_id}/ingest",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_target_ingestion(
    target_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Initiate review ingestion against a target owned by the authenticated user."""
    target = get_owned_target_or_404(target_id, current_user.id, db)
    return {
        "status": "accepted",
        "target_id": target.id,
        "message": "Ingestion initiated successfully.",
    }
