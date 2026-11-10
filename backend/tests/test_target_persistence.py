"""AnalysisTarget persistence against real MySQL. Needs TEST_DATABASE_URL."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.adapters.identity import VerifiedIdentity
from app.models import PLATFORM_GOOGLE_MAPS
from app.repositories.targets import create_target, get_target_for_owner
from app.repositories.users import get_or_create_user

URL = "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2"


def make_user(db, uid):
    return get_or_create_user(db, VerifiedIdentity(uid=uid, email=f"{uid}@example.com"))


def test_target_is_persisted_and_read_back_with_its_owner(db, session_factory):
    owner = make_user(db, "uid-a")

    created = create_target(db, owner.id, "Example Cafe", PLATFORM_GOOGLE_MAPS, URL)

    with session_factory() as other_session:  # a fresh session proves it hit the DB
        found = get_target_for_owner(other_session, created.id, owner.id)

    assert found is not None
    assert found.id == created.id
    assert found.owner_id == owner.id
    assert found.name == "Example Cafe"
    assert found.platform == PLATFORM_GOOGLE_MAPS
    assert found.source_url == URL
    assert found.created_at is not None
    assert found.updated_at is not None


def test_another_users_target_is_not_returned(db):
    a = make_user(db, "uid-a")
    b = make_user(db, "uid-b")
    target_a = create_target(db, a.id, "A's cafe", PLATFORM_GOOGLE_MAPS, URL)

    assert get_target_for_owner(db, target_a.id, b.id) is None
    assert get_target_for_owner(db, target_a.id, a.id) is not None


def test_missing_target_returns_none(db):
    owner = make_user(db, "uid-a")

    assert get_target_for_owner(db, 999999, owner.id) is None


def test_database_rejects_a_target_without_an_existing_owner(db):
    with pytest.raises(IntegrityError):
        create_target(db, 999999999, "Orphan", PLATFORM_GOOGLE_MAPS, URL)
    db.rollback()


@pytest.mark.parametrize(
    "fields",
    [
        {"name": None},
        {"platform": None},
        {"source_url": None},
    ],
)
def test_database_rejects_missing_required_fields(db, fields):
    owner = make_user(db, "uid-a")
    values = {"name": "Cafe", "platform": PLATFORM_GOOGLE_MAPS, "source_url": URL}
    values.update(fields)

    with pytest.raises(IntegrityError):
        create_target(db, owner.id, **values)
    db.rollback()
