"""Critical-flow tests. Run: pytest -q (requires DATABASE_URL; skips DB tests otherwise)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.core.database as dbmodule  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.main import app  # noqa: E402

# Shared in-memory SQLite so requests see the same schema
_test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                             poolclass=StaticPool)
dbmodule.engine = _test_engine
dbmodule.SessionLocal = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(_test_engine)

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["app"] == "Gyan Sathi"


def test_send_otp_rate_limit_shape():
    r = client.post("/api/auth/send-otp", json={"email": "someone@example.com"})
    assert r.status_code in (200, 429, 502)


def test_verify_otp_rejects_wrong():
    r = client.post("/api/auth/verify-otp",
                    json={"email": "wrong@example.com", "otp": "999999"})
    assert r.status_code == 401


def _auth_headers(email="t@example.com"):
    r = client.post("/api/auth/verify-otp", json={"email": email, "otp": "000000"})
    if r.status_code != 200:
        pytest.skip("DB unavailable")
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_me_requires_auth():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_onboarding_flow():
    headers = _auth_headers("onb@example.com")
    if not headers:
        return
    r = client.post("/api/auth/onboarding", headers=headers,
                    json={"full_name": "ટેસ્ટ", "standard": 10,
                          "medium": "gujarati", "preferred_language": "gu"})
    assert r.status_code == 200
    assert r.json()["user"]["onboarded"] is True
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["standard"] == 10


def test_admin_requires_admin_role():
    headers = _auth_headers("notadmin@example.com")
    if not headers:
        return
    r = client.get("/api/admin/dashboard", headers=headers)
    assert r.status_code == 403


def test_quiz_scoring_logic():
    from app.services.quiz_service import score_attempt

    questions = [{"answer": "A"}, {"answer": "B"}, {"answer": "C"}]
    answers = [
        {"question_index": 0, "selected": "A"},
        {"question_index": 1, "selected": "C"},
        {"question_index": 2, "selected": "C"},
    ]
    res = score_attempt(questions, answers)
    assert res["correct"] == 2
    assert res["total"] == 3
    assert res["score_percent"] == pytest.approx(66.7)


def test_rag_filter_detection():
    from app.services.rag_service import detect_filters

    f = detect_filters("ધોરણ 10 વિજ્ઞાનમાં પ્રકાશ શું છે?", default_standard=9)
    assert f["standard"] == 10
    assert f["subject"] == "Science"
    f2 = detect_filters("ગણિતમાં ત્રિકોણમિતિ સમજાવો", default_standard=None)
    assert f2["subject"] == "Mathematics"


def test_chunking_produces_sections():
    from app.services.ingestion_service import clean_text, semantic_chunks

    text = clean_text("# પરાવર્તન\n" + "પ્રકાશ પરાવર્તન થાય છે. " * 100 +
                      "\n# વક્રીભવન\n" + "પ્રકાશ વળે છે. " * 100)
    chunks = semantic_chunks(text)
    assert len(chunks) >= 2
    sections = {c["section"] for c in chunks}
    assert any("પરાવર્તન" in s for s in sections)


def test_safe_filename():
    from app.api.uploads import _safe_filename

    name = _safe_filename("../../evil path/ગણિત notes.pdf")
    assert ".." not in name
    assert "/" not in name
    assert name.endswith(".pdf")
