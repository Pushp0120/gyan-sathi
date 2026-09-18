"""Quiz API."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chapter import Chapter
from app.models.progress import StudentProgress
from app.models.quiz import QuizAttempt
from app.models.subject import Subject
from app.models.user import User
from app.schemas import QuizGenerateRequest, QuizSubmitRequest
from app.services import usage_service
from app.services.quiz_service import generate_quiz, score_attempt
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["quiz"])


@router.post("/quiz/generate")
def quiz_generate(body: QuizGenerateRequest, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    if not usage_service.rate_limit_ok("quiz_gen", user.id, 10):
        raise HTTPException(429, "થોડા સમય પછી ફરી પ્રયાસ કરો.")
    subj = db.query(Subject).filter(Subject.id == body.subject_id).first()
    if not subj:
        raise HTTPException(404, "વિષય મળ્યો નથી.")
    chapter = None
    if body.chapter_id:
        chapter = db.query(Chapter).filter(Chapter.id == body.chapter_id).first()
    try:
        questions = generate_quiz(
            db, body.standard, body.subject_id, body.chapter_id,
            subject_gu=subj.name_gu,
            chapter_gu=chapter.name_gu if chapter else "",
            count=body.count, student_id=user.id,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    usage_service.bump_usage(db, user.id, quiz_generations=1)
    return {"questions": questions, "subject": subj.to_dict(),
            "chapter": chapter.to_dict() if chapter else None}


@router.post("/quiz/submit")
def quiz_submit(body: QuizSubmitRequest,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stateless submit — the frontend has no attempt id before scoring."""
    return _score_and_store(body, user, db)


def _score_and_store(body: QuizSubmitRequest, user: User, db: Session):
    # Quiz is stateless on server: answers carry the questions from generation time.
    # We re-score using stored question bank entries matched by id/text.
    from app.models.quiz import QuizQuestion

    answers = body.answers
    if not answers or not isinstance(answers, list):
        raise HTTPException(400, "જવાબો ગુમ થયા છે.")

    correct = 0
    details = []
    for a in answers:
        qid = a.get("question_id")
        selected = (a.get("selected") or "").strip()
        q = db.query(QuizQuestion).filter(QuizQuestion.id == qid).first() if qid else None
        if q:
            right = selected == (q.correct_answer or "").strip()
        else:
            # questions may not be persisted by id (generated set); compare stored text
            right = bool(a.get("is_right"))
        if right:
            correct += 1
        details.append({"question_id": qid, "question_index": a.get("question_index"),
                        "selected": selected,
                        "correct": q.correct_answer if q else a.get("correct"),
                        "is_right": right})

    total = len(details)
    score_percent = round(correct * 100 / total, 1) if total else 0

    attempt = QuizAttempt(
        student_id=user.id, standard=user.standard,
        subject_id=answers[0].get("subject_id") if answers else None,
        chapter_id=answers[0].get("chapter_id") if answers else None,
        total_questions=total, correct_count=correct, score_percent=score_percent,
        answers=details, completed_at=utcnow(),
    )
    db.add(attempt)

    # Update progress for the chapter
    chapter_id = attempt.chapter_id
    if chapter_id:
        row = db.query(StudentProgress).filter(
            StudentProgress.student_id == user.id, StudentProgress.chapter_id == chapter_id
        ).first()
        if not row:
            row = StudentProgress(student_id=user.id, chapter_id=chapter_id,
                                  standard=user.standard, subject_id=attempt.subject_id)
            db.add(row)
        row.quiz_attempts = (row.quiz_attempts or 0) + 1
        row.best_quiz_score = max(row.best_quiz_score or 0, score_percent)
        row.last_quiz_score = score_percent
        row.completion_percent = min(100.0, (row.questions_asked or 0) * 10 +
                                     (row.quiz_attempts or 0) * 15)
        row.last_studied_at = utcnow()

    db.commit()
    return {"attempt_id": attempt.id, "total": total, "correct": correct,
            "wrong": total - correct, "score_percent": score_percent, "details": details}


@router.get("/quiz/history")
def quiz_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(50)
        .all()
    )
    return {"attempts": [r.to_dict() for r in rows]}
