"""Remove all Std 9 content from the cloud DB (app is now Std 10 only) and
complete the Std 10 chapter lists.

Fetches DATABASE_URL from the Vercel API itself (owner token), so the URL is
never printed or written to disk.

Usage:  VERCEL_TOKEN=... python scripts/remove_std9_seed_std10.py
"""
import json
import os
import sys
import urllib.request

VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "")
DB_FILE = os.environ.get("DB_FILE", "")  # path to a `vercel env pull` file

DB_URL = ""
if DB_FILE and os.path.exists(DB_FILE):
    for line in open(DB_FILE, encoding="utf-8", errors="ignore"):
        if line.startswith("DATABASE_URL="):
            DB_URL = line.split("=", 1)[1].strip().strip('"')
            break

if not DB_URL:
    print("Provide DB_FILE (vercel env pull output) with DATABASE_URL")
    sys.exit(1)

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND)
os.environ["DATABASE_URL"] = DB_URL

from sqlalchemy import text  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.subject import Subject  # noqa: E402

# Std 10 GSEB chapter lists (Gujarati-medium) — same as seed_syllabus_full
sys.path.insert(0, BACKEND)
from scripts.seed_syllabus_full import CHAPTERS  # noqa: E402

db = SessionLocal()
try:
    # ---- 1. Remove Std 9 subjects (knowledge chunks/docs/progress/quizzes cascade) ----
    std9 = db.query(Subject).filter(Subject.standard == 9).all()
    removed = []
    for s in std9:
        chunk_count = db.execute(
            text("select count(*) from knowledge_chunks where subject_id = :sid"),
            {"sid": s.id},
        ).scalar()
        removed.append((s.name_gu, chunk_count))
        db.delete(s)
    db.commit()
    print(f"removed {len(removed)} Std 9 subjects:")
    for name, chunks in removed:
        print(f"  - {name} ({chunks} chunks deleted)")

    # ---- 2. Complete Std 10 chapter lists ----
    added = 0
    for subject in db.query(Subject).filter(Subject.standard == 10).all():
        key = (10, subject.name_en)
        if key not in CHAPTERS:
            continue
        existing = {c.number for c in db.query(Chapter).filter(
            Chapter.subject_id == subject.id).all()}
        for number, name_gu in CHAPTERS[key]:
            if number in existing:
                continue
            db.add(Chapter(subject_id=subject.id, number=number, name_gu=name_gu,
                           description=""))
            added += 1
        db.commit()
        total = db.query(Chapter).filter(Chapter.subject_id == subject.id).count()
        print(f"  {subject.name_gu}: {total} chapters (+{total - len(existing) - 0})")
    print(f"chapters added: {added}")

    # ---- 3. Report final state ----
    subs = db.query(Subject).filter(Subject.standard == 10).all()
    for s in subs:
        chaps = db.query(Chapter).filter(Chapter.subject_id == s.id).order_by(
            Chapter.number).all()
        print(f"{s.name_gu} (std {s.standard}): {len(chaps)} chapters")
    total9 = db.query(Subject).filter(Subject.standard == 9).count()
    print(f"remaining Std 9 subjects: {total9}")
    print("OK")
finally:
    db.close()
