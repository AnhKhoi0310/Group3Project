from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.identity import VerifiedIdentity
from app.models import User


def _find(session: Session, firebase_uid: str) -> User | None:
    query = select(User).where(User.firebase_uid == firebase_uid)
    return session.scalars(query).one_or_none()


def get_or_create_user(session: Session, identity: VerifiedIdentity) -> User:
    """Return the user for a verified identity, creating it on first login."""
    user = _find(session, identity.uid)
    if user is None:
        user = User(firebase_uid=identity.uid, email=identity.email)
        session.add(user)
        try:
            session.commit()
            return user
        except IntegrityError:
            # A parallel first request created the row after our lookup.
            session.rollback()
            user = _find(session, identity.uid)
            if user is None:
                raise

    if identity.email is not None and user.email != identity.email:
        user.email = identity.email
        session.commit()
    return user
