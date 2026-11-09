import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import User

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session")
def alembic_config():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("CI"):
            pytest.fail("TEST_DATABASE_URL must be set in CI")
        pytest.skip("Set TEST_DATABASE_URL to run the MySQL tests")
    # These tests wipe tables, so never let them point at a real database.
    if "test" not in (make_url(url).database or ""):
        pytest.fail("TEST_DATABASE_URL must name a database containing 'test'")
    config = Config(str(ALEMBIC_INI))
    config.attributes["database_url"] = url
    return config


@pytest.fixture(scope="session")
def session_factory(alembic_config):
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    engine = create_engine(alembic_config.attributes["database_url"])
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        session.execute(delete(User))
        session.commit()
        yield session


@pytest.fixture
def client(db):
    """Provide a FastAPI TestClient instance for testing routes."""
    return TestClient(app)


class StaticVerifier:
    def __init__(self, identity: VerifiedIdentity):
        self.identity = identity

    def verify(self, token: str):
        return self.identity

    def revoke(self, uid: str):
        pass


@pytest.fixture
def user1_identity():
    return VerifiedIdentity(uid="user1-firebase-uid", email="user1@example.com")


@pytest.fixture
def user2_identity():
    return VerifiedIdentity(uid="user2-firebase-uid", email="user2@example.com")


@pytest.fixture
def auth_headers_user1(client, user1_identity, db):
    from app.repositories.users import get_or_create_user
    user = get_or_create_user(db, user1_identity)
    db.commit()
    
    app.dependency_overrides[get_verified_identity] = lambda: user1_identity
    app.dependency_overrides[get_token_verifier] = lambda: StaticVerifier(user1_identity)
    yield {"Authorization": "Bearer token-user1", "X-User-Id": user1_identity.uid, "X-Owner-Id": str(user.id)}
    app.dependency_overrides.clear()


@pytest.fixture
def target_owned_by_user2(client, user2_identity, db):
    from app.repositories.users import get_or_create_user
    user2 = get_or_create_user(db, user2_identity)
    db.commit()

    target = AnalysisTarget(owner_id=user2.id, name="User 2 Secret Target")
    db.add(target)
    db.commit()
    db.refresh(target)
    return target.id
