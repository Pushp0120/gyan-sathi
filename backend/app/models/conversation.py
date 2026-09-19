"""Chat conversations and messages (with RAG source metadata)."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, JSONType
from app.utils.text_sanitizer import sanitize_gujarati
from app.utils.time import utcnow


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(200), default="નવો સંવાદ")
    standard = Column(Integer, nullable=True)
    subject_id = Column(String(36), nullable=True)
    chapter_id = Column(String(36), nullable=True)
    is_archived = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def to_dict(self, with_messages: bool = False) -> dict:
        d = {
            "id": self.id,
            "title": sanitize_gujarati(self.title),
            "standard": self.standard,
            "subject_id": self.subject_id,
            "chapter_id": self.chapter_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if with_messages:
            d["messages"] = [m.to_dict() for m in self.messages]
        return d


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    mode = Column(String(30), default="ask")   # ask|explain|exam|summary|mcq|quiz|practice|important
    sources = Column(JSONType, default=list)      # RAG source metadata per message
    used_rag = Column(Boolean, default=False)
    feedback = Column(String(10), nullable=True)  # up | down
    tokens_used = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    def to_dict(self) -> dict:
        # Sanitize on read so answers saved before mixed-script guarding still render clean.
        return {
            "id": self.id,
            "role": self.role,
            "content": sanitize_gujarati(self.content),
            "mode": self.mode,
            "sources": self.sources or [],
            "used_rag": bool(self.used_rag),
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
