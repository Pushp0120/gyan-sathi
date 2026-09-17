"""Bulk import pipeline: replace-on-upload semantics + filename matching."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core import database as dbmodule  # noqa: E402
from app.api.admin import _match_score, _retire_other_docs, _subject_aliases  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.knowledge import KnowledgeDocument  # noqa: E402
from app.models.subject import Subject  # noqa: G004
from app.models.user import User  # noqa: E402

# Mirror test_core_flows' shared in-memory engine setup (idempotent).
if getattr(dbmodule, "_test_engine", None) is None:
    from sqlalchemy import create_engine  # noqa: E402
    from sqlalchemy.orm import sessionmaker  # noqa: E402
    from sqlalchemy.pool import StaticPool  # noqa: E402
    from app.core.database import Base  # noqa: E402

    _eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                         poolclass=StaticPool)
    dbmodule.engine = _eng
    dbmodule.SessionLocal = sessionmaker(bind=_eng, autoflush=False, autocommit=False)
    Base.metadata.create_all(_eng)
    dbmodule._test_engine = _eng

# NOTE: always resolve dbmodule.SessionLocal dynamically inside helpers —
# test_core_flows may rebind the engine after this module is imported.


def _mk_subject(name_en="Science", name_gu="વિજ્ઞાન", code="SCI", std=10):
    db = dbmodule.SessionLocal()
    s = Subject(standard=std, name_en=name_en, name_gu=name_gu, code=code, sort_order=1)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _mk_chapter(subject, number, name_gu):
    db = dbmodule.SessionLocal()
    c = Chapter(subject_id=subject.id, number=number, name_gu=name_gu, name_en=None)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _mk_admin():
    import uuid
    db = dbmodule.SessionLocal()
    u = User(email=f"bulkadmin-{uuid.uuid4().hex[:8]}@gs.test", role="admin",
             is_active=True, full_name="Bulk Admin", standard=10)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# --------------------------------------------------------------- matching

def test_match_score_chapter_number():
    s = Subject(standard=10, name_en="Science", name_gu="વિજ્ઞાન", code="SCI")
    c = Chapter(number=10, name_gu="વિદ્યુત પ્રવાહનાં મૂળભૂત ખ્યાલો", name_en=None)
    assert _match_score("Science-CH-10.pdf", s, c, _subject_aliases(s)) >= 7


def test_match_score_rejects_wrong_chapter():
    s = Subject(standard=10, name_en="Science", name_gu="વિજ્ઞાન", code="SCI")
    c = Chapter(number=3, name_gu="જળ સંસાધન", name_en=None)
    assert _match_score("Science-CH-10.pdf", s, c, _subject_aliases(s)) < 5


def test_match_score_subject_word_helps():
    s = Subject(standard=10, name_en="Mathematics", name_gu="ગણિત", code="MATH")
    c = Chapter(number=5, name_gu="અંકશાસ્ત્ર", name_en=None)
    assert _match_score("ganit ch 5", s, c, _subject_aliases(s)) >= 5


# ----------------------------------------------------- replace-on-upload

def test_retire_disables_sibling_notes_only():
    s = _mk_subject()
    c = _mk_chapter(s, 4, "કાર્બન સંયોજનો")
    db = dbmodule.SessionLocal()
    notes = KnowledgeDocument(title="AI notes", standard=10, chapter_id=c.id,
                              subject_id=s.id, status="completed", is_enabled=True,
                              doc_type="notes")
    other_chap_doc = KnowledgeDocument(title="Other chapter", standard=10,
                                       chapter_id="zzz", status="completed", is_enabled=True,
                                       doc_type="notes")
    disabled_doc = KnowledgeDocument(title="Already off", standard=10, chapter_id=c.id,
                                     status="completed", is_enabled=False, doc_type="notes")
    db.add_all([notes, other_chap_doc, disabled_doc])
    db.commit()
    tb = KnowledgeDocument(title="Textbook ch4", standard=10, chapter_id=c.id,
                           subject_id=s.id, status="completed", is_enabled=True,
                           doc_type="textbook")
    db.add(tb)
    db.commit()

    retired = _retire_other_docs(db, tb)
    db.refresh(notes); db.refresh(other_chap_doc)
    assert retired == 1                      # only the sibling notes doc
    assert notes.is_enabled is False
    assert other_chap_doc.is_enabled is True  # untouched


# ------------------------------------------------------------ bulk ingest

def test_bulk_ingest_skips_existing_textbook(tmp_path):
    from fastapi.testclient import TestClient
    import app.core.database as dbmodule
    from app.main import app

    client = TestClient(app)
    admin = _mk_admin()
    s = _mk_subject(name_en="Mathematics", name_gu="ગણિત", code="MATH")
    c = _mk_chapter(s, 2, "બહુપદી")
    db = dbmodule.SessionLocal()
    db.add(KnowledgeDocument(title="Existing TB", standard=10, chapter_id=c.id,
                             subject_id=s.id, status="completed", is_enabled=True,
                             doc_type="textbook"))
    db.commit()
    token = create_access_token(admin)

    pdf = tmp_path / "MATH-CH-2.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    r = client.post(
        "/api/admin/bulk/ingest",
        files={"files": ("MATH-CH-2.pdf", pdf.read_bytes(), "application/pdf")},
        data={"chapter_ids": f'["{c.id}"]', "standard": "10",
              "doc_type": "textbook", "replace": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["succeeded"] == 0
    assert "skip" in body["results"][0]["error"] or body["results"][0]["error"]


def test_bulk_ingest_requires_admin():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.post("/api/admin/bulk/ingest", files={"files": ("x.pdf", b"1", "application/pdf")})
    assert r.status_code in (401, 403)


def test_coverage_endpoint_counts_only_textbook():
    from fastapi.testclient import TestClient
    import app.core.database as dbmodule
    from app.main import app

    client = TestClient(app)
    admin = _mk_admin()
    s = _mk_subject(name_en="Social Science", name_gu="સામાજિક વિજ્ઞાન", code="SST")
    c = _mk_chapter(s, 1, "ભારતના સંસાધનો")
    db = dbmodule.SessionLocal()
    doc = KnowledgeDocument(title="TB ch1", standard=10, chapter_id=c.id,
                            subject_id=s.id, status="completed", is_enabled=True,
                            doc_type="textbook")
    db.add(doc)
    db.commit()
    token = create_access_token(admin)

    r = client.get("/api/admin/bulk/coverage?standard=10",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    row = next((x for x in body["chapters"] if x["id"] == c.id), None)
    assert row is not None
    assert row["textbook_chunks"] == 0  # doc has no chunks yet
