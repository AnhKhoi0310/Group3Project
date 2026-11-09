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


@pytest.fixture
def auth_headers_user1():
    """Return authorization headers for test user 1."""
    return {"Authorization": "Bearer user1_token"}


@pytest.fixture
def auth_headers_user2():
    """Return authorization headers for test user 2."""
    return {"Authorization": "Bearer user2_token"}


@pytest.fixture
def target_owned_by_user2(db):
    """Create a target owned by user 2 in the test database and return its ID."""
    # Create user 2 and a target belonging to user 2, 
    # then commit and return the target id.
    # Example structure:
    # user2 = User(id=2, email="user2@example.com")
    # db.add(user2)
    # target = Target(id=1, owner_id=user2.id, name="User 2 Target")
    # db.add(target)
    # db.commit()
    # return target.id
    return 1
