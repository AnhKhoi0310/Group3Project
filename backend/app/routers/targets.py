from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.models.target import AnalysisTarget
from app.models.user import User
from app.schemas.target import AnalysisTargetRead
from app.services.target_service import (
    get_target_for_owner,
    list_targets_for_owner,
)

router = APIRouter(prefix="/targets", tags=["targets"])


@router.get("/", response_model=list[AnalysisTargetRead])
def list_targets(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AnalysisTarget]:
    """List all analysis targets for the authenticated user."""
    return list_targets_for_owner(db, owner_id=current_user.id)


@router.get("/{target_id}", response_model=AnalysisTargetRead)
def get_target(
    target_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalysisTarget:
    """Get a specific target only if it belongs to the authenticated user."""
    target = get_target_for_owner(db, target_id=target_id, owner_id=current_user.id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    return target
