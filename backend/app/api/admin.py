"""Admin API (role=admin only)."""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        chunks = ingestion_service.process_document(db, doc, data, ext)
    except Exception as exc:
        raise HTTPException(422, f"પ્રક્રિયા નિષ્ફળ: {str(exc)[:200]}")
    return {"ok": True, "document": doc.to_dict(), "chunks": chunks}


@router.post("/knowledge/{doc_id}/reprocess")
def reprocess_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "દસ્તાવેજ મળ્યો નથી.")
    try:
        data, ftype = ingestion_service.fetch_document_bytes(doc)
        chunks = ingestion_service.process_document(db, doc, data, ftype)
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
    sql = """
        SELECT content, standard, subject_name_gu, chapter_name_gu, page_number,
               section, source, embedding <=> :vec::vector AS distance
        FROM knowledge_chunks
        WHERE is_enabled = true AND embedding IS NOT NULL
    """
    params: dict = {"vec": vec_literal}
    if body.standard:
        sql += " AND standard = :std"
        params["std"] = body.standard
    sql += " ORDER BY embedding <=> :vec::vector LIMIT :k"
    params["k"] = body.top_k
    rows = db.execute(sql, params)
    return {"results": [dict(r._mapping) for r in rows]}


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
