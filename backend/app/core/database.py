"""Database engine/session for managed Postgres — Neon, Supabase, Docker pgvector."""
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

# Portable JSON: native JSONB on Postgres, plain JSON elsewhere (tests/SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")

settings = get_settings()

_is_postgres = settings.database_url.startswith("postgresql")

_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_postgres:
    _engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

engine = create_engine(
    settings.database_url,
    **_engine_kwargs,
)

if _is_postgres:
    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):
        # Supabase installs pgvector into the `extensions` schema; include it so
        # the `vector` type resolves. Applied as a post-connect SET (a normal
        # query) because startup-packet options are rejected by Neon's pooler.
        cursor = dbapi_connection.cursor()
        cursor.execute("SET search_path TO public, extensions")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
