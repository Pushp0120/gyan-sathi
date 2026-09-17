"""Document ingestion pipeline: extract → clean → chunk → embed → store."""
import logging
import re

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.ai_service import get_ai_provider
from app.services.embedding_service import embed_texts

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 1200
MIN_CHUNK_CHARS = 80


# ---------------------------------------------------------------- extraction

def extract_text_from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(data))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            t = page.extract_text() or ""
            pages.append(f"[[page:{i}]]\n{t}")
        return "\n".join(pages)
    except Exception as exc:
        logger.error("PDF extract failed: %s", exc)
        raise ValueError("PDF માંથી ટેક્સ્ટ મેળવી શકાયો નથી (scanned PDF હોઈ શકે).")


def extract_text_from_docx(data: bytes) -> str:
    try:
        import io

        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        logger.error("DOCX extract failed: %s", exc)
        raise ValueError("DOCX માંથી ટેક્સ્ટ મેળવી શકાયો નથી.")


def extract_text(data: bytes, file_type: str) -> str:
    if file_type == "pdf":
        return extract_text_from_pdf(data)
    if file_type == "docx":
        return extract_text_from_docx(data)
    return data.decode("utf-8", errors="replace")


# -------------------------------------------------------------------- clean

PAGE_MARK_RE = re.compile(r"\[\[page:(\d+)\]\]")


def clean_text(raw: str) -> str:
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def split_with_pages(text: str) -> list[tuple[str, int | None]]:
    """Split cleaned text into (segment, page_number) pieces using page markers."""
    segments = []
    last = 0
    for m in PAGE_MARK_RE.finditer(text):
        seg = text[last:m.start()].strip()
        if seg:
            segments.append((seg, int(m.group(1))))
        last = m.end()
        _ = m.group(1)
    tail = text[last:].strip()
    if tail:
        segments.append((tail, None))
    return segments or [(text, None)]


# ------------------------------------------------------------------ chunking

HEADING_RE = re.compile(r"^(?:#+\s+.*|પ્રકરણ.*|એકમ.*|[0-9]+[\.\)]\s+\S.*|[A-Z][A-Za-z ]{3,60}$)")


def semantic_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[dict]:
    """Section-aware chunking: split by headings first, then pack paragraphs."""
    chunks: list[dict] = []
    lines = text.split("\n")
    sections: list[tuple[str, list[str]]] = [("સામાન્ય", [])]
    for ln in lines:
        s = ln.strip()
        if s and len(s) < 120 and (s.startswith("#") or HEADING_RE.match(s)):
            sections.append((s.lstrip("# "), []))
        else:
            sections[-1][1].append(ln)

    for sec_title, sec_lines in sections:
        buf: list[str] = []
        size = 0
        for ln in sec_lines:
            ln = ln.strip()
            if not ln:
                continue
            if size + len(ln) > max_chars and buf:
                chunks.append({"section": sec_title, "content": "\n".join(buf).strip()})
                buf, size = [], 0
            buf.append(ln)
            size += len(ln) + 1
        if buf:
            content = "\n".join(buf).strip()
            if len(content) >= MIN_CHUNK_CHARS:
                chunks.append({"section": sec_title, "content": content})
            elif chunks:
                # merge tiny trailing fragment into previous chunk of same section
                prev = chunks[-1]
                if prev["section"] == sec_title and len(prev["content"]) + len(content) <= max_chars:
                    prev["content"] += "\n" + content
                else:
                    chunks.append({"section": sec_title, "content": content})
    return chunks


# ----------------------------------------------------------------- pipeline

def process_text(db: Session, document: KnowledgeDocument, cleaned: str) -> int:
    """Chunk + embed already-extracted text. Returns number of chunks stored."""
    document.status = "processing"
    db.commit()

    try:
        if len(clean_text(cleaned)) < 20:
            raise ValueError("દસ્તાવેજમાં પૂરતો ટેક્સ્ટ મળ્યો નથી.")

        # Keep the extracted text (with [[page:N]] markers) so re-ingestion and
        # re-embedding never need the original file — essential on serverless,
        # where the filesystem is ephemeral.
        document.raw_text = cleaned[:2_000_000]

        # Clear old chunks if re-ingesting
        db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()

        all_chunks: list[dict] = []
        for segment, page_no in split_with_pages(cleaned):
            for ch in semantic_chunks(segment):
                ch["page_number"] = page_no
                all_chunks.append(ch)

        if not all_chunks:
            raise ValueError("છૂંકીઓ (chunks) બની શકી નથી.")

        # Embeddings (passage input type)
        texts = [c["content"] for c in all_chunks]
        try:
            vectors = embed_texts(texts, input_type="passage")
        except Exception:
            vectors = [[] for _ in texts]

        subject_gu = ""
        chapter_gu = ""
        chapter_no = None
        if document.subject_id:
            from app.models.subject import Subject
            subj = db.query(Subject).get(document.subject_id)
            if subj:
                subject_gu = subj.name_gu
        if document.chapter_id:
            from app.models.chapter import Chapter
            chap = db.query(Chapter).get(document.chapter_id)
            if chap:
                chapter_gu = chap.name_gu
                chapter_no = chap.number

        rows = []
        for i, c in enumerate(all_chunks):
            rows.append(KnowledgeChunk(
                document_id=document.id,
                chapter_id=document.chapter_id,
                chunk_index=i,
                content=c["content"],
                standard=document.standard,
                subject_id=document.subject_id,
                chapter_number=chapter_no,
                chapter_name_gu=chapter_gu,
                subject_name_gu=subject_gu,
                language=document.language,
                page_number=c.get("page_number"),
                section=(c["section"] or "")[:200],
                source=document.title,
                academic_year=document.academic_year,
                source_type=document.source_type,
                doc_type=(getattr(document, "doc_type", None) or "notes"),
                doc_metadata={"document_title": document.title},
                embedding=vectors[i] if i < len(vectors) and vectors[i] else None,
            ))
        db.add_all(rows)
        document.chunk_count = len(rows)
        document.status = "completed"
        document.error_message = ""
        db.commit()
        logger.info("Document %s ingested: %d chunks", document.id, len(rows))
        return len(rows)
    except Exception as exc:
        document.status = "failed"
        document.error_message = str(exc)[:500]
        db.commit()
        logger.exception("Ingestion failed for %s", document.id)
        raise


def process_document(db: Session, document: KnowledgeDocument, data: bytes, file_type: str) -> int:
    """Extract text from raw file bytes, then run the full pipeline."""
    cleaned = clean_text(extract_text(data, file_type))
    return process_text(db, document, cleaned)


def fetch_document_text(doc: KnowledgeDocument) -> str:
    """Text to (re)ingest from: DB-stored extracted text, local file, or storage."""
    if getattr(doc, "raw_text", None):
        return doc.raw_text
    if doc.stored_path:
        import os

        with open(doc.stored_path, "rb") as f:
            data = f.read()
        ftype = (doc.file_name or "").rsplit(".", 1)[-1].lower()
        return clean_text(extract_text(data, ftype))
    raise ValueError("દસ્તાવેજનું લખાણ મળ્યું નથી — ફાઇલ ફરી અપલોડ કરો.")
