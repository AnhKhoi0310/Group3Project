from app.models.target import AnalysisTarget
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_target_for_owner(
    db: Session, target_id: int, owner_id: int
) -> AnalysisTarget | None:
    """Fetch an analysis target only if it belongs to the authenticated owner."""
    return db.scalar(
        select(AnalysisTarget).where(
            AnalysisTarget.id == target_id,
            AnalysisTarget.owner_id == owner_id,
        )
    )

def list_targets_for_owner(db: Session, owner_id: int) -> list[AnalysisTarget]:
    """List all analysis targets belonging to the authenticated owner."""
    return list(
        db.scalars(
            select(AnalysisTarget).where(AnalysisTarget.owner_id == owner_id)
        ).all()
    )
