"""Student progress API."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chapter import Chapter
from app.models.conversation import Message
from app.models.progress import StudentProgress
from app.models.quiz import QuizAttempt
from app.models.subject import Subject
from app.models.user import User

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/progress")
def get_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    questions_asked = (
        db.query(func.count(Message.id))
        .join(__import__("app.models.conversation", fromlist=["Conversation"]).Conversation)
        .filter(Message.role == "user")
        .filter(__import__("app.models.conversation", fromlist=["Conversation"]).Conversation.student_id == user.id)
        .scalar() or 0
    )
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(10)
        .all()
    )
    progress_rows = (
        db.query(StudentProgress, Chapter, Subject)
        .join(Chapter, Chapter.id == StudentProgress.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id, isouter=True)
        .filter(StudentProgress.student_id == user.id)
        .order_by(StudentProgress.last_studied_at.desc())
        .limit(30)
        .all()
    )
    by_subject: dict = {}
    for prog, chap, subj in progress_rows:
        key = subj.id if subj else "unknown"
        entry = by_subject.setdefault(key, {
            "subject_id": subj.id if subj else None,
            "name_gu": subj.name_gu if subj else "અન્ય",
            "icon": subj.icon if subj else "📚",
            "chapters": 0,
            "avg_completion": 0,
        })
        entry["chapters"] += 1
        entry["avg_completion"] += prog.completion_percent or 0
    subjects_out = []
    for e in by_subject.values():
        if e["chapters"]:
            e["avg_completion"] = round(e["avg_completion"] / e["chapters"], 1)
        subjects_out.append(e)

    return {
        "questions_asked": questions_asked,
        "quiz_attempts": len(attempts),
        "chapters_studied": len(progress_rows),
        "streak_days": user.streak_days or 0,
        "recent_quiz": [a.to_dict() for a in attempts[:5]],
        "subjects": subjects_out,
        "chapters": [
            {**p.to_dict(), "chapter_name": c.name_gu, "chapter_number": c.number,
             "subject_name": s.name_gu if s else "", "subject_icon": s.icon if s else "📚"}
            for p, c, s in progress_rows
        ],
    }
