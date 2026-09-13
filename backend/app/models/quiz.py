"""Quizzes: generated questions and student attempts."""
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
)

from app.core.database import Base, JSONType
from app.utils.time import utcnow


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    standard = Column(Integer, index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=True)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), index=True, nullable=True)
    question_type = Column(String(20), default="mcq")  # mcq | short | long
    question_text = Column(Text, nullable=False)
    options = Column(JSONType, default=list)     # ["વિકલ્પ A", ...] for MCQ
    correct_answer = Column(Text, default="")
    explanation = Column(Text, default="")
    difficulty = Column(String(20), default="medium")  # easy | medium | hard
    source = Column(String(300), default="")
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self, include_answer: bool = False) -> dict:
        d = {
            "id": self.id,
            "question_type": self.question_type,
            "question_text": self.question_text,
            "options": self.options or [],
            "difficulty": self.difficulty,
        }
        if include_answer:
            d["correct_answer"] = self.correct_answer
            d["explanation"] = self.explanation
            d["source"] = self.source
        return d


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (Index("ix_quiz_attempts_student", "student_id", "started_at"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    standard = Column(Integer, nullable=True)
    subject_id = Column(String(36), nullable=True)
    chapter_id = Column(String(36), nullable=True)
    total_questions = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    score_percent = Column(Float, default=0)
    answers = Column(JSONType, default=list)  # [{question_id, selected, correct, is_right}]
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "standard": self.standard,
            "subject_id": self.subject_id,
            "chapter_id": self.chapter_id,
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "score_percent": self.score_percent,
            "answers": self.answers or [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
