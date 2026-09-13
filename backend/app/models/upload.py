"""Uploads: student file uploads tracked server-side against the plan limit."""
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base, JSONType
from app.utils.time import utcnow


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)

    original_name = Column(String(300), default="")
    stored_path = Column(String(500), default="")        # local disk path
    storage_url = Column(String(600), default="")        # Supabase Storage URL (if configured)
    storage_bucket = Column(String(100), default="uploads")
    storage_object = Column(String(500), default="")
    mime_type = Column(String(120), default="")
    file_size = Column(BigInteger, default=0)
    file_type = Column(String(20), default="")           # pdf|image|text|docx

    extracted_text = Column(Text, default="")
    analysis_status = Column(String(20), default="pending")  # pending|completed|failed
    analysis_result = Column(JSONType, default=dict)

    # Snapshot of the allowance state at upload time (audit trail)
    uploads_used_after = Column(Integer, default=0)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "storage_url": self.storage_url,
            "analysis_status": self.analysis_status,
            "analysis_result": self.analysis_result or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
