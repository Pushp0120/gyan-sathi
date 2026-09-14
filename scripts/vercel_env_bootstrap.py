"""Prepare the Neon/Supabase cloud database and run the full Gyan Sathi seed.

Usage (from repo root), so the URL never lands in a file or argv history:
    GS_DB_URL='postgresql://...' python scripts/vercel_env_bootstrap.py
"""
import os
import sys

DB_URL = os.environ.get("GS_DB_URL", "")
if not DB_URL:
    print("Set GS_DB_URL env var (pasted inline), e.g.:")
    print("  GS_DB_URL='postgresql://...' python scripts/vercel_env_bootstrap.py")
    sys.exit(1)

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND)
os.environ["DATABASE_URL"] = DB_URL

# NVIDIA key for embedding generation during KB seed — read from backend/.env if present
_env_path = os.path.join(BACKEND, ".env")
if os.path.exists(_env_path) and not os.environ.get("NVIDIA_API_KEY"):
    for _line in open(_env_path, encoding="utf-8", errors="ignore"):
        if _line.startswith("NVIDIA_API_KEY="):
            os.environ["NVIDIA_API_KEY"] = _line.split("=", 1)[1].strip()
            break

# ---- 1. Connect + inspect + prepare ----
from sqlalchemy import create_engine, text  # noqa: E402

engine = create_engine(DB_URL, connect_args={"connect_timeout": 20, "sslmode": "require"})
with engine.connect() as c:
    ver = c.execute(text("select version()")).scalar()
    print("server:", ver.split(",")[0])
    has_vector = c.execute(text("select 1 from pg_extension where extname='vector'")).scalar()
    if not has_vector:
        print("enabling pgvector…")
        c.execute(text("create extension if not exists vector"))
        c.commit()
        print("pgvector: ENABLED")
    else:
        print("pgvector: already installed")
    n = c.execute(text("select count(*) from information_schema.tables where table_schema='public'")).scalar()
    print(f"existing public tables: {n}")

# ---- 2. Create all tables via SQLAlchemy models ----
from app.core.database import Base
from app.models import *  # noqa: F401,F403  (register every model)

print("creating tables…")
Base.metadata.create_all(engine)

# ---- 3. ivfflat ANN index (idempotent, after tables exist) ----
# NOTE: ivfflat/hnsw on plain `vector` cap at 2000 dims; our embeddings are 2048.
# Use a halfvec HNSW index (pgvector >= 0.7) on the cast column; if unsupported,
# continue without ANN — retrieval still works via exact scan at this scale.
with engine.connect() as c:
    pgv_ver = c.execute(text("select extversion from pg_extension where extname='vector'")).scalar()
    print("pgvector version:", pgv_ver)
    c.execute(text("""
        do $$
        begin
          if exists (select 1 from information_schema.tables
                     where table_schema='public' and table_name='knowledge_chunks') then
            begin
              execute 'create index if not exists ix_kc_embedding on knowledge_chunks
                       using hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)';
              raise notice 'halfvec HNSW index created';
            exception when others then
              raise notice 'ANN index skipped: %', sqlerrm;
            end;
          end if;
        end $$;
    """))
    c.commit()
print("vector ANN index: ensured")

# ---- 4. Support indexes from schema.sql (idempotent) ----
support = [
    "create index if not exists ix_users_email on users (email)",
    "create index if not exists ix_users_standard on users (standard)",
    "create index if not exists ix_chapters_subject on chapters (subject_id)",
    "create index if not exists ix_conversations_student on conversations (student_id)",
    "create index if not exists ix_messages_conversation on messages (conversation_id)",
    "create index if not exists ix_uploads_student on uploads (student_id)",
    "create index if not exists ix_subscriptions_student on subscriptions (student_id)",
    "create index if not exists ix_subscriptions_status on subscriptions (status)",
]
with engine.connect() as c:
    for stmt in support:
        c.execute(text(stmt))
    c.commit()
print("support indexes: ensured")

# ---- 5. Seed (seed_database.py does its own settings/db wiring; env is already set) ----
print("== seeding ==")
import subprocess
result = subprocess.run(
    [sys.executable, "-m", "scripts.seed_database"],
    cwd=BACKEND, env=os.environ, capture_output=True, text=True,
)
print(result.stdout[-2000:] if result.stdout else "(no stdout)")
if result.returncode != 0:
    print("SEED STDERR:", result.stderr[-3000:])
    sys.exit(1)

# ---- 6. Verify ----
print("== verification ==")
from app.core.database import SessionLocal  # type: ignore
from app.models.user import User
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.subscription import Plan

db = SessionLocal()
try:
    print("plans:", [(p.code, p.price_inr) for p in db.query(Plan).all()])
    subs = db.query(Subject).count()
    chaps = db.query(Chapter).count()
    docs = db.query(KnowledgeDocument).count()
    chunks = db.query(KnowledgeChunk).count()
    admins = db.query(User).filter(User.role == "admin").count()
    print(f"subjects: {subs} | chapters: {chaps} | knowledge docs: {docs} | chunks: {chunks} | admins: {admins}")
    assert subs >= 8 and chunks > 0 and admins >= 1, "seed incomplete!"
    print("ALL GREEN")
finally:
    db.close()
