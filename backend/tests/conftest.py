import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db import get_session
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
    """Use the test database session for requests made by API tests."""
    app.dependency_overrides[get_session] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
