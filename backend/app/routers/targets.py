import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.errors import ApiError
from app.models import PLATFORM_GOOGLE_MAPS, AnalysisTarget, User
from app.repositories.targets import create_target, list_targets_for_owner
from app.schemas import TargetCreate, TargetRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/targets")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TargetRead)
def create_analysis_target(
    payload: TargetCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AnalysisTarget:
    try:
        return create_target(
            session,
            owner_id=user.id,  # only ever the verified user
            name=payload.name,
            platform=PLATFORM_GOOGLE_MAPS,
            source_url=payload.source_url,
        )
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Could not create a target for user %s", user.id)
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None


@router.get("", response_model=list[TargetRead])
def list_my_targets(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[AnalysisTarget]:
    try:
        return list_targets_for_owner(session, owner_id=user.id)
    except SQLAlchemyError:
        logger.exception("Could not list targets for user %s", user.id)
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None
