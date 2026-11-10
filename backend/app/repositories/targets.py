
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, User


def get_owned_target(
    session: Session,
    target_id: int,
    user: User,
) -> AnalysisTarget | None:
    query = select(AnalysisTarget).where(
        AnalysisTarget.id == target_id,
        AnalysisTarget.owner_id == user.id,
    )

    return session.scalars(query).one_or_none()
