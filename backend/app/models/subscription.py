"""Plans, subscriptions, payments, usage."""
import uuid
from datetime import timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.core.database import Base, JSONType
from app.utils.time import utcnow


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(30), unique=True, index=True, nullable=False)  # free | premium
    name_en = Column(String(100), default="")
    name_gu = Column(String(100), default="")
    price_inr = Column(Integer, default=0)
    duration_days = Column(Integer, default=0)  # 0 = unlimited
    upload_limit = Column(Integer, default=10)  # -1 = unlimited
    chat_daily_limit = Column(Integer, default=-1)  # -1 = unlimited
    features = Column(JSONType, default=list)
    is_active = Column(Boolean, default=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name_en": self.name_en,
            "name_gu": self.name_gu,
            "price_inr": self.price_inr,
            "duration_days": self.duration_days,
            "upload_limit": self.upload_limit,
            "chat_daily_limit": self.chat_daily_limit,
            "features": self.features or [],
        }


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_student_status", "student_id", "status"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), default="active", index=True)  # active | expired | cancelled
    started_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    plan = relationship("Plan")

    def is_premium(self) -> bool:
        if self.status != "active" or self.plan is None or self.plan.code != "premium":
            return False
        if self.expires_at is None:
            return True
        exp = self.expires_at
        now = utcnow()
        # normalize naive/aware comparisons
        if exp.tzinfo is None:
            from datetime import datetime

            exp = exp.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return exp > now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "plan": self.plan.to_dict() if self.plan else None,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_premium": self.is_premium(),
        }


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=True)
    gateway = Column(String(30), default="razorpay")
    gateway_order_id = Column(String(120), default="")
    gateway_payment_id = Column(String(120), default="", index=True)
    gateway_signature = Column(String(300), default="")
    amount_inr = Column(Integer, default=0)
    status = Column(String(20), default="created", index=True)  # created|paid|failed|refunded
    mode = Column(String(20), default="sandbox")
    notes = Column(JSONType, default=dict)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "gateway": self.gateway,
            "gateway_order_id": self.gateway_order_id,
            "gateway_payment_id": self.gateway_payment_id,
            "amount_inr": self.amount_inr,
            "status": self.status,
            "mode": self.mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


class Usage(Base):
    """Daily usage counters per student (persisted from Redis)."""
    __tablename__ = "usage"
    __table_args__ = (Index("ix_usage_student_date", "student_id", "usage_date"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    usage_date = Column(Date, default=utcnow().date, nullable=False)
    ai_requests = Column(Integer, default=0)
    uploads = Column(Integer, default=0)
    quiz_generations = Column(Integer, default=0)
    tokens_used = Column(BigInteger, default=0)

    def to_dict(self) -> dict:
        return {
            "date": self.usage_date.isoformat() if self.usage_date else None,
            "ai_requests": self.ai_requests,
            "uploads": self.uploads,
            "quiz_generations": self.quiz_generations,
            "tokens_used": self.tokens_used,
        }
