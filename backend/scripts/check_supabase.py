"""Verify the Supabase connection before starting the app.

Run:  python -m scripts.check_supabase
Checks: connectivity, pgvector extension, schema access, table creation rights.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()


def main() -> int:
    print("=" * 50)
    print("Gyan Sathi — Supabase connection check")
    print("=" * 50)

    url = settings.database_url
    if not url or url.startswith("sqlite"):
        print("✘ DATABASE_URL is not set to a Postgres/Supabase URL.")
        print("  Set it in backend/.env to your Supabase session pooler URI:")
        print("  postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres")
        return 1
    safe = url.split("@")[-1] if "@" in url else url
    print(f"→ Target: {safe}")

    failures = 0

    # 1) connectivity
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            print(f"✔ Connected — {version.split(',')[0]}")
    except Exception as exc:
        print(f"✘ Connection failed: {exc}")
        print("  Tips: use the SESSION POOLER URI (port 5432), include the")
        print("  project ref in the username, and check the DB password.")
        return 1

    # 2) pgvector extension
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            )).first()
            if row:
                print("✔ pgvector extension installed")
            else:
                print("✘ pgvector NOT installed. Run in Supabase SQL editor:")
                print("    create extension if not exists vector;")
                failures += 1
    except Exception as exc:
        print(f"✘ Extension check failed: {exc}")
        failures += 1

    # 3) can we resolve the vector type (search_path includes extensions)?
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT '[0,1,2]'::vector"))
            print("✔ vector type resolves (search_path OK)")
    except Exception:
        print("✘ vector type not resolvable — search_path must include 'extensions'.")
        print("  The backend now sets search_path automatically; restart it.")
        failures += 1

    # 4) write access (can create tables)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS _gs_check (id int)"))
            conn.execute(text("DROP TABLE _gs_check"))
        print("✔ Schema write access OK")
    except Exception as exc:
        print(f"✘ Write test failed: {exc}")
        failures += 1

    # 5) Supabase auth config (informational)
    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("⚠ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set —")
        print("  email OTP will fall back to dev mode (OTP 000000).")
    else:
        print(f"✔ Supabase auth configured ({settings.supabase_url})")

    print("-" * 50)
    if failures:
        print(f"{failures} issue(s) found — fix them, then re-run this check.")
        return 1
    print("All checks passed ✔ — you can run the backend and seed script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
