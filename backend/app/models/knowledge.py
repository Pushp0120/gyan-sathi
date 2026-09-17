"""Knowledge base: documents and vector chunks for RAG."""
import uuid

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
)
from app.vectors import Vector
from sqlalchemy.orm import relationship

from app.core.config import get_settings
from app.core.database import Base, JSONType
from app.utils.time import utcnow

settings = get_settings()
EMBED_DIM = settings.ai_embedding_dim


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(300), nullable=False)
    source_type = Column(String(40), default="curated")  # gseb | textbook | question_bank | curated | demo
    doc_type = Column(String(20), default="notes", index=True)  # textbook | notes
    standard = Column(Integer, index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    academic_year = Column(String(10), default="2026-27")
    language = Column(String(10), default="gu")
    file_name = Column(String(300), default="")
    raw_text = Column(Text, default="")  # extracted text kept for re-ingestion without the original file
    status = Column(String(20), default="pending", index=True)  # pending|processing|completed|failed
    error_message = Column(Text, default="")
    chunk_count = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type,
            "doc_type": self.doc_type or "notes",
            "standard": self.standard,
            "subject_id": self.subject_id,
            "chapter_id": self.chapter_id,
            "academic_year": self.academic_year,
            "language": self.language,
            "file_name": self.file_name,
            "status": self.status,
            "error_message": self.error_message,
            "chunk_count": self.chunk_count,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)

    # RAG metadata (filterable)
    standard = Column(Integer, index=True)
    subject_id = Column(String(36), index=True)
    chapter_number = Column(Integer, nullable=True)
    chapter_name_gu = Column(String(200), default="")
    subject_name_gu = Column(String(120), default="")
    language = Column(String(10), default="gu")
    page_number = Column(Integer, nullable=True)
    section = Column(String(200), default="")
    source = Column(String(300), default="")
    academic_year = Column(String(10), default="2026-27")
    source_type = Column(String(40), default="curated")
    doc_type = Column(String(20), default="notes", index=True)  # textbook | notes
    doc_metadata = Column(JSONType, default=dict)
    is_enabled = Column(Boolean, default=True)

    embedding = Column(Vector(EMBED_DIM), nullable=True)

    document = relationship("KnowledgeDocument", back_populates="chunks")

    __table_args__ = (
        Index("ix_kc_standard_chapter", "standard", "chapter_id"),
    )

    def to_dict(self, include_content: bool = True) -> dict:
        d = {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "standard": self.standard,
            "subject_name_gu": self.subject_name_gu,
            "chapter_name_gu": self.chapter_name_gu,
            "chapter_number": self.chapter_number,
            "language": self.language,
            "page_number": self.page_number,
            "section": self.section,
            "source": self.source,
            "academic_year": self.academic_year,
            "source_type": self.source_type,
            "doc_type": self.doc_type or "notes",
        }
        if include_content:
            d["content"] = self.content
        return d
