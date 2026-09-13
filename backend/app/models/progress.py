"""Student progress tracking and answer feedback."""
import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
)

from app.core.database import Base
from app.utils.time import utcnow


class StudentProgress(Base):
    __tablename__ = "student_progress"
    __table_args__ = (
        UniqueConstraint("student_id", "chapter_id", name="uq_progress_student_chapter"),
        Index("ix_progress_student", "student_id", "subject_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    standard = Column(Integer, nullable=True)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)

    questions_asked = Column(Integer, default=0)
    quiz_attempts = Column(Integer, default=0)
    best_quiz_score = Column(Float, default=0)
    last_quiz_score = Column(Float, default=0)
    completion_percent = Column(Float, default=0)  # heuristic: min(100, signals*20)
    last_studied_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "standard": self.standard,
            "subject_id": self.subject_id,
            "chapter_id": self.chapter_id,
            "questions_asked": self.questions_asked,
            "quiz_attempts": self.quiz_attempts,
            "best_quiz_score": self.best_quiz_score,
            "last_quiz_score": self.last_quiz_score,
            "completion_percent": self.completion_percent,
            "last_studied_at": self.last_studied_at.isoformat() if self.last_studied_at else None,
        }


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    rating = Column(String(10), nullable=False)  # up | down
    comment = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
