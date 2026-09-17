"""Admin API (role=admin only)."""
import logging
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.chapter import Chapter
from app.models.conversation import Conversation, Message
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.progress import Feedback, StudentProgress
from app.models.quiz import QuizAttempt, QuizQuestion
from app.models.subject import Subject
from app.models.subscription import Payment, Plan, Subscription
from app.models.upload import Upload
from app.models.user import User
from app.schemas import (
    AdminStudentUpdate, ChapterCreate, DocumentMeta, KnowledgeSearchRequest, SubjectCreate,
)
from app.services import ingestion_service
from sqlalchemy import text as text_sql
from app.services.embedding_service import embed_query
from app.services.rag_service import build_rag_context
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/admin", tags=["admin"],
                   dependencies=[Depends(get_current_admin)])


# ------------------------------------------------------------- dashboard

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total_students = db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0
    active_students = db.query(func.count(User.id)).filter(User.role == "student", User.is_active == True).scalar() or 0  # noqa: E712
    premium_ids = {
        s.student_id for s in db.query(Subscription).filter(Subscription.status == "active").all()
        if s.is_premium()
    }
    total_questions = (
        db.query(func.count(Message.id))
        .filter(Message.role == "user")
        .scalar() or 0
    )
    total_uploads = db.query(func.count(Upload.id)).scalar() or 0
    total_ai_requests = (
        db.query(func.coalesce(func.sum(Message.tokens_used), 0)).scalar() or 0
    )
    revenue = (
        db.query(func.coalesce(func.sum(Payment.amount_inr), 0))
        .filter(Payment.status == "paid").scalar() or 0
    )
    popular_subjects = _popular_subjects(db)
    recent_activity = _recent_activity(db)
    return {
        "total_students": total_students,
        "active_students": active_students,
        "premium_students": len(premium_ids),
        "free_students": max(0, total_students - len(premium_ids)),
        "total_questions": total_questions,
        "total_uploads": total_uploads,
        "total_tokens": int(total_ai_requests),
        "revenue_inr": int(revenue),
        "popular_subjects": popular_subjects,
        "recent_activity": recent_activity,
    }


def _popular_subjects(db: Session):
    rows = (
        db.query(Subject.name_gu, func.count(StudentProgress.id))
        .join(StudentProgress, StudentProgress.subject_id == Subject.id)
        .group_by(Subject.name_gu)
        .order_by(func.count(StudentProgress.id).desc())
        .limit(6)
        .all()
    )
    return [{"name": r[0], "count": r[1]} for r in rows]


def _recent_activity(db: Session, limit: int = 15):
    msgs = (
        db.query(Message, Conversation, User)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(User, User.id == Conversation.student_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "when": m.created_at.isoformat() if m.created_at else None,
            "student": u.full_name or u.email,
            "type": m.role,
            "preview": (m.content or "")[:80],
        }
        for m, c, u in msgs
    ]


# -------------------------------------------------------------- students

@router.get("/students")
def list_students(q: str | None = None, standard: int | None = None,
                  db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == "student")
    if q:
        query = query.filter((User.email.ilike(f"%{q}%")) | (User.full_name.ilike(f"%{q}%")))
    if standard:
        query = query.filter(User.standard == standard)
    students = query.order_by(User.created_at.desc()).limit(200).all()
    premium_ids = {
        s.student_id for s in db.query(Subscription).filter(Subscription.status == "active").all()
        if s.is_premium()
    }
    out = []
    for s in students:
        d = s.to_dict()
        d["is_premium"] = s.id in premium_ids
        d["questions_asked"] = (
            db.query(func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .filter(Conversation.student_id == s.id, Message.role == "user")
            .scalar() or 0
        )
        d["uploads"] = db.query(func.count(Upload.id)).filter(Upload.student_id == s.id).scalar() or 0
        out.append(d)
    return {"students": out}


@router.patch("/students/{student_id}")
def update_student(student_id: str, body: AdminStudentUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == student_id).first()
    if not user:
        raise HTTPException(404, "વિદ્યાર્થી મળ્યો નથી.")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None and body.role in ("student", "admin", "teacher"):
        user.role = body.role
    db.commit()
    return {"ok": True, "student": user.to_dict()}


# -------------------------------------------------- subjects & chapters

@router.post("/subjects")
def create_subject(body: SubjectCreate, db: Session = Depends(get_db)):
    s = Subject(standard=body.standard, name_en=body.name_en, name_gu=body.name_gu,
                code=body.code, icon=body.icon, sort_order=body.sort_order)
    db.add(s)
    db.commit()
    return {"ok": True, "subject": s.to_dict()}


@router.patch("/subjects/{subject_id}")
def update_subject(subject_id: str, body: SubjectCreate, db: Session = Depends(get_db)):
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(404, "વિષય મળ્યો નથી.")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return {"ok": True, "subject": s.to_dict()}


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: str, db: Session = Depends(get_db)):
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(404, "વિષય મળ્યો નથી.")
    s.is_active = False
    db.commit()
    return {"ok": True}


@router.post("/chapters")
def create_chapter(body: ChapterCreate, db: Session = Depends(get_db)):
    c = Chapter(subject_id=body.subject_id, number=body.number,
                name_en=body.name_en, name_gu=body.name_gu, description=body.description)
    db.add(c)
    db.commit()
    return {"ok": True, "chapter": c.to_dict()}


@router.delete("/chapters/{chapter_id}")
def delete_chapter(chapter_id: str, db: Session = Depends(get_db)):
    c = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not c:
        raise HTTPException(404, "પ્રકરણ મળ્યું નથી.")
    c.is_active = False
    db.commit()
    return {"ok": True}


# ------------------------------------------------------- knowledge base

@router.get("/knowledge")
def list_documents(db: Session = Depends(get_db)):
    docs = (
        db.query(KnowledgeDocument)
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(200)
        .all()
    )
    return {"documents": [d.to_dict() for d in docs]}


@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    title: str = "",
    standard: int = 10,
    subject_id: str | None = None,
    chapter_id: str | None = None,
    source_type: str = "curated",
    doc_type: str = "notes",
    replace: bool = False,
    academic_year: str = "2026-27",
    language: str = "gu",
    db: Session = Depends(get_db),
):
    data = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "txt", "md", "docx"):
        raise HTTPException(400, "માત્ર PDF, TXT, MD, DOCX માન્ય છે.")
    doc = KnowledgeDocument(
        title=title or (file.filename or "document")[:300],
        source_type=source_type, standard=standard, subject_id=subject_id,
        chapter_id=chapter_id, academic_year=academic_year, language=language,
        file_name=file.filename or "", status="pending",
        doc_type=doc_type if doc_type in ("textbook", "notes") else "notes",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        chunks = ingestion_service.process_document(db, doc, data, ext)
    except Exception as exc:
        raise HTTPException(422, f"પ્રક્રિયા નિષ્ફળ: {str(exc)[:200]}")
    replaced = 0
    if replace and doc.is_enabled and doc.status == "completed" and chapter_id:
        replaced = _retire_other_docs(db, doc)
    return {"ok": True, "document": doc.to_dict(), "chunks": chunks, "retired_docs": replaced}


@router.post("/knowledge/text")
def ingest_text(body: dict, db: Session = Depends(get_db)):
    """Ingest pasted text (syllabus, notes, chapter summaries) without a file."""
    text = str(body.get("text") or "").strip()
    if len(text) < 50:
        raise HTTPException(400, "ઓછામાં ઓછું 50 અક્ષરોનું લખાણ આપો.")
    doc_type = str(body.get("doc_type") or "notes")
    doc = KnowledgeDocument(
        title=str(body.get("title") or "Pasted text")[:300],
        source_type=str(body.get("source_type") or "curated"),
        standard=int(body.get("standard") or 10),
        subject_id=body.get("subject_id") or None,
        chapter_id=body.get("chapter_id") or None,
        academic_year=str(body.get("academic_year") or "2026-27"),
        language=str(body.get("language") or "gu"),
        file_name="", status="pending",
        doc_type=doc_type if doc_type in ("textbook", "notes") else "notes",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    try:
        chunks = ingestion_service.process_text(db, doc, text)
    except Exception as exc:
        raise HTTPException(422, f"પ્રક્રિયા નિષ્ફળ: {str(exc)[:200]}")
    return {"ok": True, "document": doc.to_dict(), "chunks": chunks}


@router.post("/knowledge/{doc_id}/reprocess")
def reprocess_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "દસ્તાવેજ મળ્યો નથી.")
    try:
        text = ingestion_service.fetch_document_text(doc)
        chunks = ingestion_service.process_text(db, doc, text)
        return {"ok": True, "chunks": chunks, "document": doc.to_dict()}
    except Exception as exc:
        raise HTTPException(422, f"પ્રક્રિયા નિષ્ફળ: {str(exc)[:200]}")


@router.patch("/knowledge/{doc_id}")
def toggle_document(doc_id: str, body: dict, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "દસ્તાવેજ મળ્યો નથી.")
    if "is_enabled" in body:
        doc.is_enabled = bool(body["is_enabled"])
    if "title" in body:
        doc.title = str(body["title"])[:300]
    db.commit()
    return {"ok": True, "document": doc.to_dict()}


@router.delete("/knowledge/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "દસ્તાવેજ મળ્યો નથી.")
    db.delete(doc)
    db.commit()
    return {"ok": True}


@router.post("/knowledge/search")
def knowledge_search(body: KnowledgeSearchRequest, db: Session = Depends(get_db)):
    is_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
    if not is_pg:
        words = [w for w in body.query.split() if len(w) > 2] or [body.query]
        conds = " OR ".join(["content LIKE :w" + str(i) for i in range(len(words))])
        params = {f"w{i}": f"%{w}%" for i, w in enumerate(words)}
        params["k"] = body.top_k
        rows = db.execute(
            text_sql(f"""SELECT content, standard, subject_name_gu, chapter_name_gu,
                        page_number, section, source, 1.0 AS distance
                        FROM knowledge_chunks WHERE {conds} LIMIT :k"""),
            params,
        )
        return {"results": [dict(r._mapping) for r in rows]}
    qvec = embed_query(body.query)
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in qvec) + "]"
    distance_expr = "embedding::halfvec(2048) <=> CAST(:vec AS halfvec)"
    sql = f"""
        SELECT content, standard, subject_name_gu, chapter_name_gu, page_number,
               section, source, {distance_expr} AS distance
        FROM knowledge_chunks
        WHERE is_enabled = true AND embedding IS NOT NULL
    """
    params: dict = {"vec": vec_literal}
    if body.standard:
        sql += " AND standard = :std"
        params["std"] = body.standard
    sql += f" ORDER BY {distance_expr} LIMIT :k"
    params["k"] = body.top_k
    rows = db.execute(text_sql(sql), params)
    return {"results": [dict(r._mapping) for r in rows]}


# ------------------------------------------------------- bulk import

def _retire_other_docs(db: Session, doc: KnowledgeDocument) -> int:
    """Disable sibling documents for the same chapter (same subject when unattached).

    Used when a textbook upload replaces AI-generated notes: old docs are
    disabled rather than deleted, so nothing is lost and they can be re-enabled.
    """
    q = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id != doc.id,
        KnowledgeDocument.standard == doc.standard,
        KnowledgeDocument.is_enabled == True,  # noqa: E712
    )
    if doc.chapter_id:
        q = q.filter(KnowledgeDocument.chapter_id == doc.chapter_id)
    else:
        q = q.filter(KnowledgeDocument.chapter_id.is_(None),
                     KnowledgeDocument.subject_id == doc.subject_id)
    retired = 0
    for other in q.all():
        other.is_enabled = False
        retired += 1
    db.commit()
    return retired


def _subject_aliases(s: Subject) -> set[str]:
    aliases = {(s.name_en or ""), (s.name_gu or ""), (s.code or "")}
    extra = {
        "Mathematics": {"maths", "math", "ganit"},
        "Science": {"sci", "vignan"},
        "Social Science": {"social", "sst", "samajik"},
        "English": {"eng"},
        "Gujarati": {"guj"},
        "Hindi": {"hin"},
        "Sanskrit": {"sans"},
        "ICT": {"computer"},
    }.get(s.name_en, set())
    return {a.lower() for a in aliases if a} | {a.lower() for a in extra}


def _transliterations(word: str) -> set[str]:
    """Common Gujarati-name transliteration variants of a romanized word."""
    w = word.lower().strip()
    out = {w}
    for a, b in (("aa", "a"), ("ee", "i"), ("oo", "u"),
                 ("kh", "k"), ("gh", "g"), ("ch", "c"), ("jh", "j"),
                 ("th", "t"), ("dh", "d"), ("ph", "p"), ("bh", "b"),
                 ("sh", "s"), ("v", "b"), ("w", "v")):
        if a in w:
            out.add(w.replace(a, b))
    return out


def _match_score(filename: str, subject: Subject, chapter: Chapter, aliases: set[str]) -> float:
    base = filename.rsplit(".", 1)[0].lower()
    file_tokens = [p for p in re.split(r"[^a-z0-9\u0A80-\u0AFF]+", base) if p]
    score = 0.0
    if any(a in base for a in aliases if len(a) > 2):
        score += 3
    m = re.search(r"(?:ch|chapter|prakaran|prakaran)\D{0,3}(\d{1,2})", base) \
        or re.match(r"(\d{1,2})\b", base)
    if m and int(m.group(1)) == chapter.number:
        score += 4
    name_variants: set[str] = set()
    for name in (chapter.name_gu or "", chapter.name_en or ""):
        for tok in re.split(r"[^a-z0-9\u0A80-\u0AFF]+", name.lower()):
            if len(tok) >= 3:
                name_variants |= _transliterations(tok)
    for tok in file_tokens:
        if len(tok) >= 3 and _transliterations(tok) & name_variants:
            score += 2
    return score


@router.get("/bulk/candidates")
def bulk_candidates(standard: int = 10, db: Session = Depends(get_db)):
    """Chapters a bulk upload can target, with their current document status."""
    subjects = db.query(Subject).filter(
        Subject.standard == standard, Subject.is_active == True).all()  # noqa: E712
    out = []
    for s in subjects:
        ch_list = []
        for c in (db.query(Chapter)
                  .filter(Chapter.subject_id == s.id, Chapter.is_active == True)  # noqa: E712
                  .order_by(Chapter.number).all()):
            docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.chapter_id == c.id).all()
            enabled = [d for d in docs if d.is_enabled]
            types = {(getattr(d, "doc_type", None) or "notes") for d in enabled}
            ch_list.append({
                "id": c.id, "number": c.number,
                "name_gu": c.name_gu, "name_en": c.name_en,
                "has_textbook": "textbook" in types,
                "has_notes": "notes" in types,
                "doc_count": len(enabled),
            })
        out.append({"id": s.id, "name_gu": s.name_gu, "name_en": s.name_en, "chapters": ch_list})
    return {"subjects": out}


@router.post("/bulk/match")
def bulk_match(body: dict, db: Session = Depends(get_db)):
    """Match uploaded filenames to chapters (number in name + subject + fuzzy title)."""
    files = [str(f) for f in (body.get("files") or []) if str(f).strip()]
    standard = int(body.get("standard") or 10)
    subjects = db.query(Subject).filter(
        Subject.standard == standard, Subject.is_active == True).all()  # noqa: E712
    matches = []
    for f in files:
        best, best_score, best_subject = None, 0.0, None
        for s in subjects:
            aliases = _subject_aliases(s)
            for c in db.query(Chapter).filter(
                    Chapter.subject_id == s.id, Chapter.is_active == True).all():  # noqa: E712
                score = _match_score(f, s, c, aliases)
                if score > best_score:
                    best, best_score, best_subject = c, score, s
        matches.append({
            "file": f,
            "chapter_id": best.id if best else None,
            "chapter_number": best.number if best else None,
            "chapter_name_gu": best.name_gu if best else None,
            "subject_id": best_subject.id if best_subject else None,
            "subject_name_gu": best_subject.name_gu if best_subject else None,
            "confidence": round(best_score, 2),
            "confident": best_score >= 5,
        })
    return {"matches": matches}


@router.post("/bulk/ingest")
async def bulk_ingest(
    files: list[UploadFile] = File(...),
    chapter_ids: str = Form("[]"),
    standard: int = Form(10),
    subject_id: str | None = Form(None),
    doc_type: str = Form("textbook"),
    replace: bool = Form(True),
    language: str = Form("gu"),
    db: Session = Depends(get_db),
):
    """Ingest a batch of chapter PDFs (<=10 per call, serverless-friendly).

    Each file must map to a chapter (pre-resolved by /bulk/match or chosen in
    the UI). Chapters already covered by enabled textbook docs are skipped.
    """
    import json as _json
    try:
        ids = _json.loads(chapter_ids or "[]")
    except Exception:
        ids = []
    if not files:
        raise HTTPException(400, "કોઈ ફાઇલ મળી નથી.")
    if len(files) > 10:
        raise HTTPException(400, "એક જ વખતે મહત્તમ 10 ફાઇલ અપલોડ કરો.")
    if doc_type not in ("textbook", "notes"):
        doc_type = "textbook"

    results = []
    succeeded = 0
    for i, f in enumerate(files):
        cid = ids[i] if i < len(ids) and ids[i] else None
        entry = {"file": f.filename, "ok": False, "chunks": 0,
                 "error": None, "document_id": None, "retired_docs": 0}
        try:
            ext = (f.filename or "").rsplit(".", 1)[-1].lower()
            if ext not in ("pdf", "txt", "md", "docx"):
                raise ValueError("ફાઇલ પ્રકાર માન્ય નથી (PDF/TXT/MD/DOCX).")
            chapter = db.query(Chapter).filter(Chapter.id == cid).first() if cid else None
            if not chapter:
                raise ValueError("પ્રકરણ મળ્યું નથી — ફાઇલ છોડી દેવાઈ.")
            # Skip chapters that already have an enabled textbook document.
            existing = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.chapter_id == cid,
                KnowledgeDocument.doc_type == "textbook",
                KnowledgeDocument.is_enabled == True,  # noqa: E712
            ).count()
            if existing:
                raise ValueError("આ પ્રકરણમાં પાઠ્યપુસ્તક પહેલેથી છે — સ્કિપ કરેલ.")
            data = await f.read()
            doc = KnowledgeDocument(
                title=(f.filename or "document")[:300],
                source_type="textbook" if doc_type == "textbook" else "curated",
                standard=standard,
                subject_id=chapter.subject_id or subject_id,
                chapter_id=cid,
                academic_year="2026-27", language=language,
                file_name=f.filename or "", status="pending", doc_type=doc_type,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            entry["chunks"] = ingestion_service.process_document(db, doc, data, ext)
            entry["ok"] = True
            entry["document_id"] = doc.id
            succeeded += 1
            if replace:
                entry["retired_docs"] = _retire_other_docs(db, doc)
        except Exception as exc:
            entry["error"] = str(exc)[:200]
        results.append(entry)
    return {"ok": succeeded > 0, "succeeded": succeeded, "total": len(files), "results": results}


@router.get("/bulk/coverage")
def bulk_coverage(standard: int = 10, db: Session = Depends(get_db)):
    """Textbook coverage: how many active chapters have real textbook chunks."""
    subjects = db.query(Subject).filter(
        Subject.standard == standard, Subject.is_active == True).all()  # noqa: E712
    subj_gu = {s.id: s.name_gu for s in subjects}
    chapters = (db.query(Chapter)
                .filter(Chapter.subject_id.in_(subj_gu.keys()),
                        Chapter.is_active == True)  # noqa: E712
                .order_by(Chapter.number).all())
    counts = (
        db.query(KnowledgeChunk.chapter_id, func.count(KnowledgeChunk.id))
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .filter(
            KnowledgeChunk.is_enabled == True,  # noqa: E712
            KnowledgeDocument.is_enabled == True,  # noqa: E712
            KnowledgeDocument.doc_type == "textbook",
            KnowledgeDocument.standard == standard,
        )
        .group_by(KnowledgeChunk.chapter_id)
        .all()
    )
    textbook_chunks = {cid: n for cid, n in counts}
    covered = sum(1 for c in chapters if textbook_chunks.get(c.id))
    return {
        "standard": standard,
        "total_chapters": len(chapters),
        "textbook_chapters": covered,
        "chapters": [
            {
                "id": c.id, "number": c.number, "name_gu": c.name_gu,
                "subject_gu": subj_gu.get(c.subject_id, ""),
                "textbook_chunks": textbook_chunks.get(c.id, 0),
            }
            for c in chapters
        ],
    }


# ------------------------------------------------ subscriptions/payments

@router.get("/subscriptions")
def list_subscriptions(db: Session = Depends(get_db)):
    subs = (
        db.query(Subscription, User, Plan)
        .join(User, User.id == Subscription.student_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .order_by(Subscription.created_at.desc())
        .limit(200)
        .all()
    )
    return {"subscriptions": [
        {**s.to_dict(), "student_email": u.email} for s, u, p in subs
    ]}


@router.get("/payments")
def list_payments(db: Session = Depends(get_db)):
    pays = (
        db.query(Payment, User)
        .join(User, User.id == Payment.student_id)
        .order_by(Payment.created_at.desc())
        .limit(200)
        .all()
    )
    return {"payments": [{**p.to_dict(), "student_email": u.email} for p, u in pays]}


@router.get("/feedback")
def list_feedback(db: Session = Depends(get_db)):
    rows = (
        db.query(Feedback, User, Message)
        .join(User, User.id == Feedback.student_id)
        .join(Message, Message.id == Feedback.message_id)
        .order_by(Feedback.created_at.desc())
        .limit(100)
        .all()
    )
    return {"feedback": [
        {**f.to_dict(), "student_email": u.email, "message_preview": (m.content or "")[:150]}
        for f, u, m in rows
    ]}


@router.get("/quiz-questions")
def list_quiz_questions(db: Session = Depends(get_db)):
    rows = db.query(QuizQuestion).order_by(QuizQuestion.created_at.desc()).limit(100).all()
    return {"questions": [q.to_dict(include_answer=True) for q in rows]}
