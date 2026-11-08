from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.config import get_settings
from app.db import Base

url = context.config.attributes.get("database_url")
if url is None:
    url = get_settings().database_url.get_secret_value()

engine = create_engine(url, poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
