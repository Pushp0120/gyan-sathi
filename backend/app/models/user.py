"""User / student model."""
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String

from app.core.database import Base
from app.utils.time import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), default="")
    password_hash = Column(String(255), default="")  # set when password auth is used
    role = Column(String(20), default="student", index=True)  # student | admin | teacher
    is_active = Column(Boolean, default=True)

    # Onboarding
    standard = Column(Integer, nullable=True)          # 9 | 10
    medium = Column(String(20), default="gujarati")    # gujarati | english
    preferred_language = Column(String(10), default="gu")
    onboarded = Column(Boolean, default=False)

    # Progress extras
    streak_days = Column(Integer, default=0)
    last_active_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "standard": self.standard,
            "medium": self.medium,
            "preferred_language": self.preferred_language,
            "onboarded": self.onboarded,
            "streak_days": self.streak_days or 0,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
