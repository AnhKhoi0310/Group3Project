from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget


def create_target(
    session: Session,
    owner_id: int,
    name: str,
    platform: str,
    source_url: str,
) -> AnalysisTarget:
    """Persist a target for the given owner. Callers pass the verified user's id."""
    target = AnalysisTarget(
        owner_id=owner_id, name=name, platform=platform, source_url=source_url
    )
    session.add(target)
    session.commit()
    return target


def get_target_for_owner(
    session: Session, target_id: int, owner_id: int
) -> AnalysisTarget | None:
    """Fetch by id AND owner together, so other users' targets are never returned."""
    query = select(AnalysisTarget).where(
        AnalysisTarget.id == target_id,
        AnalysisTarget.owner_id == owner_id,
    )
    return session.scalars(query).one_or_none()


def list_targets_for_owner(session: Session, owner_id: int) -> list[AnalysisTarget]:
    """Return only this owner's targets, newest first."""
    query = (
        select(AnalysisTarget)
        .where(AnalysisTarget.owner_id == owner_id)
        .order_by(AnalysisTarget.created_at.desc(), AnalysisTarget.id.desc())
    )
    return list(session.scalars(query).all())


def update_target_for_owner(
    session: Session,
    target_id: int,
    owner_id: int,
    *,
    name: str | None = None,
    source_url: str | None = None,
) -> AnalysisTarget | None:
    """Update permitted fields only when the target belongs to this owner."""
    target = get_target_for_owner(session, target_id, owner_id)

    if target is None:
        return None

    if name is not None:
        target.name = name

    if source_url is not None:
        target.source_url = source_url

    session.commit()
    return target
