"""Academic subjects (from DB, never hard-coded in frontend)."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base
from app.utils.time import utcnow


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    standard = Column(Integer, nullable=False, index=True)  # 9 | 10
    name_en = Column(String(120), nullable=False)           # Science
    name_gu = Column(String(120), nullable=False)           # વિજ્ઞાન
    code = Column(String(40), default="")
    icon = Column(String(16), default="📘")
    color = Column(String(20), default="navy")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "standard": self.standard,
            "name_en": self.name_en,
            "name_gu": self.name_gu,
            "code": self.code,
            "icon": self.icon,
            "color": self.color,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }
