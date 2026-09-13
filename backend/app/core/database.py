"""Database engine/session for Supabase Postgres (with pgvector types)."""
from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

# Portable JSON: native JSONB on Postgres, plain JSON elsewhere (tests/SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")

settings = get_settings()

_connect_args: dict = {}
_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("postgresql"):
    # Supabase installs pgvector (and other extensions) into the `extensions`
    # schema — include it on the search_path so the `vector` type resolves.
    _connect_args = {"options": "-csearch_path=public,extensions"}
    _engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
