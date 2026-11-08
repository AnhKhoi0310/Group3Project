"""User mapping against real MySQL. Needs TEST_DATABASE_URL (see README)."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.adapters.identity import VerifiedIdentity
from app.auth import get_verified_identity
from app.db import get_session
from app.main import app
from app.models import User
from app.repositories.users import get_or_create_user

USER_A = VerifiedIdentity(uid="uid-a", email="a@example.com")
USER_B = VerifiedIdentity(uid="uid-b", email="b@example.com")


def user_count(session):
    session.rollback()  # end the snapshot so other sessions' commits are visible
    return session.scalar(select(func.count()).select_from(User))


def test_first_login_creates_a_user_and_later_logins_reuse_it(db):
    first = get_or_create_user(db, USER_A)
    second = get_or_create_user(db, USER_A)

    assert first.id == second.id
    assert (first.firebase_uid, first.email) == ("uid-a", "a@example.com")
    assert user_count(db) == 1


def test_different_identities_get_different_users(db):
    a = get_or_create_user(db, USER_A)
    b = get_or_create_user(db, USER_B)

    assert a.id != b.id


def test_uids_differing_only_by_case_are_different_users(db):
    lower = get_or_create_user(db, VerifiedIdentity(uid="abc123", email=None))
    upper = get_or_create_user(db, VerifiedIdentity(uid="ABC123", email=None))

    assert lower.id != upper.id
    assert user_count(db) == 2


def test_new_email_from_the_provider_updates_the_same_user(db):
    original = get_or_create_user(db, USER_A)
    changed = VerifiedIdentity(uid="uid-a", email="new@example.com")

    updated = get_or_create_user(db, changed)

    assert updated.id == original.id
    assert updated.email == "new@example.com"


def test_token_without_email_keeps_the_stored_email(db):
    get_or_create_user(db, USER_A)

    user = get_or_create_user(db, VerifiedIdentity(uid="uid-a", email=None))

    assert user.email == "a@example.com"


def test_database_rejects_a_duplicate_uid(db):
    db.add_all([User(firebase_uid="same"), User(firebase_uid="same")])

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_parallel_first_requests_create_one_user(db, session_factory):
    def login(_):
        with session_factory() as session:
            return get_or_create_user(session, USER_A).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = set(pool.map(login, range(8)))

    assert len(ids) == 1
    assert user_count(db) == 1


def test_client_supplied_ids_do_not_change_the_mapped_user(db, session_factory):
    b = get_or_create_user(db, USER_B)

    def session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_verified_identity] = lambda: USER_A
    app.dependency_overrides[get_session] = session_override
    try:
        response = TestClient(app).get(
            f"/api/me?uid=uid-b&user_id={b.id}",
            headers={"X-User-Id": "uid-b", "X-Owner-Id": str(b.id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.json() == {"uid": "uid-a", "email": "a@example.com"}
    assert user_count(db) == 2
    db.refresh(b)
    assert b.email == "b@example.com"


def test_models_match_the_migrations(alembic_config, session_factory):
    command.check(alembic_config)
