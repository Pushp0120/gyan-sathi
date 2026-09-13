"""Chapters under a subject."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.core.database import Base
from app.utils.time import utcnow


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False)
    number = Column(Integer, nullable=False)
    name_en = Column(String(200), default="")
    name_gu = Column(String(200), default="")
    description = Column(String(500), default="")
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "number": self.number,
            "name_en": self.name_en,
            "name_gu": self.name_gu,
            "description": self.description,
            "is_active": self.is_active,
        }
