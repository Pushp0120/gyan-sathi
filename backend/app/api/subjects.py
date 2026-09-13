"""Subjects & chapters API (data-driven, no hard-coding in frontend)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chapter import Chapter
from app.models.subject import Subject
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/api", tags=["subjects"])


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
