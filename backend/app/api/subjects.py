"""Subjects & chapters API (data-driven, no hard-coding in frontend)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chapter import Chapter
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.subject import Subject
from app.models.user import User
from app.core.security import get_current_user
from app.utils.text_sanitizer import sanitize_gujarati

router = APIRouter(prefix="/api", tags=["subjects"])

# Official GCERT/GSEB Std 10 textbooks (Gujarati medium), hosted on
# Google Drive. Each entry is a Drive FILE_ID; the API returns an embed
# link (used by the in-app reader iframe) and a download link.
# Keyed by lowercase subject name; ICT uses the Computer Studies book.
# To swap a book: replace the FILE_ID with the new file's Drive ID.
TEXTBOOK_PDFS: dict[str, str] = {
    "mathematics": "1oMG5TK1AJXoYt5KYzmJlXoDQYoGDa-sY",
    "science": "183xOEaxK9HzWf1dbFTCNgPqqg58P2ovI",
    "social science": "1-Gng2JOtCrtifyWi6RPAUbOow5-sDdoB",
    "gujarati": "1M8lpCqt9JkoDKJkcs1AOI-NhO09h45mm",
    "english": "1UPXxXTIbRSWa-BC3YVRMP6sOK57KMHXx",
    "hindi": "18LZAAoQO15h2l8CxYIOuFPoGJDt4N7_O",
    "sanskrit": "1j4t7rH7RwoGFXwnepwKCR-qlCC90BDKL",
    "ict": "12zafbTYgmsIr-Vrl8ap2472_hA9SzN0U",
}


def _drive_embed_url(file_id: str) -> str:
    """Drive viewer URL suitable for embedding in an iframe."""
    return f"https://drive.google.com/file/d/{file_id}/preview"


def _drive_download_url(file_id: str) -> str:
    """Direct download URL for a Drive file."""
    return f"https://drive.google.com/uc?export=download&id={file_id}"


@router.get("/subjects")
def list_subjects(standard: int | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(Subject).filter(Subject.is_active == True)  # noqa: E712
    if standard:
        q = q.filter(Subject.standard == standard)
    subs = q.order_by(Subject.sort_order, Subject.name_en).all()
    return {"subjects": [s.to_dict() for s in subs]}


@router.get("/subjects/{subject_id}/chapters")
def list_chapters(subject_id: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "વિષય મળ્યો નથી.")
    chapters = (
        db.query(Chapter)
        .filter(Chapter.subject_id == subject_id, Chapter.is_active == True)  # noqa: E712
        .order_by(Chapter.number)
        .all()
    )
    return {"subject": subj.to_dict(), "chapters": [c.to_dict() for c in chapters]}


@router.get("/chapters/{chapter_id}/content")
def chapter_content(chapter_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Reading content for a chapter — the ingested knowledge-base text."""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(404, "પ્રકરણ મળ્યું નથી.")
    chunks = (
        db.query(KnowledgeChunk)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .filter(
            KnowledgeChunk.chapter_id == chapter_id,
            KnowledgeChunk.is_enabled == True,  # noqa: E712
            # Retired (replaced) documents must not surface in the reader.
            KnowledgeDocument.is_enabled == True,  # noqa: E712
        )
        # Real textbook content first, AI-generated notes after — so uploading
        # a textbook PDF upgrades the reader without deleting anything.
        .order_by(
            case((KnowledgeChunk.doc_type == "textbook", 0), else_=1),
            KnowledgeChunk.chunk_index,
        )
        .all()
    )
    subject = db.query(Subject).filter(Subject.id == chapter.subject_id).first()
    return {
        "chapter": chapter.to_dict(),
        "subject": subject.to_dict() if subject else None,
        "sections": [sanitize_gujarati(c.content) for c in chunks],
    }


@router.get("/subjects/{subject_id}/textbook")
def subject_textbook(subject_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Full official textbook PDF for a subject (hosted on Google Drive)."""
    subj = db.query(Subject).filter(Subject.id == subject_id, Subject.is_active == True).first()  # noqa: E712
    if not subj:
        raise HTTPException(404, "વિષય મળ્યો નથી.")
    file_id = TEXTBOOK_PDFS.get((subj.name_en or "").strip().lower())
    if not file_id or file_id.startswith("DRIVE_FILE_ID_"):
        # Not configured yet (or placeholder) — frontend shows a friendly message.
        return {"subject": subj.to_dict(), "pdf_url": None, "download_url": None}
    return {
        "subject": subj.to_dict(),
        "pdf_url": _drive_embed_url(file_id),
        "download_url": _drive_download_url(file_id),
    }
