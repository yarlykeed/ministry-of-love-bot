from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine as sa_create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from ministry.config import DATABASE_URL
from ministry.models import Base


def create_engine(url: str, **kwargs: Any) -> Engine:
    engine = sa_create_engine(url, **kwargs)

    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked.
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_engine(DATABASE_URL)

# Usage: `with SessionLocal.begin() as session:` commits on success
# and rolls back on error.
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db() -> None:
    url = make_url(DATABASE_URL)

    if url.get_backend_name() == "sqlite" and url.database:
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(engine)
