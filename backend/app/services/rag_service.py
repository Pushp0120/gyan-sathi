"""RAG service: retrieval + context building for the tutor."""
import logging

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services import cache_service
from app.services.embedding_service import embed_query

logger = logging.getLogger(__name__)
settings = get_settings()

# Gujarati + English keyword triggers for subject/chapter filters
SUBJECT_KEYWORDS = {
    "Science": ["વિજ્ઞાન", "science", "ભૌતિક", "રસાયણ", "જીવવિજ્ઞાન"],
    "Mathematics": ["ગણિત", "math", "maths", "mathematics"],
    "Social Science": ["સામાજિક", "social"],
    "Gujarati": ["ગુજરાતી"],
    "English": ["અંગ્રેજી", "english"],
    "Hindi": ["હિન્દી", "hindi"],
    "Sanskrit": ["સંસ્કૃત"],
    "ICT": ["કમ્પ્યુટર", "ict"],
}

STANDARD_PATTERNS = ["ધોરણ 9", "ધોરણ 10", "std 9", "std 10", "standard 9", "standard 10",
                     "class 9", "class 10", "9 ના", "10 ના"]


def detect_filters(question: str, default_standard: int | None = None) -> dict:
    """Extract standard/subject hints from the question text."""
    q = question.lower()
    standard = None
    for pat in ["ધોરણ 10", "std 10", "standard 10", "class 10", "10 ના"]:
        if pat in q:
            standard = 10
            break
    if not standard:
        for pat in ["ધોરણ 9", "std 9", "standard 9", "class 9", "9 ના"]:
            if pat in q:
                standard = 9
                break
    subject = None
    for subj, kws in SUBJECT_KEYWORDS.items():
        if any(k in q for k in kws):
            subject = subj
            break
    return {"standard": standard or default_standard, "subject": subject}


def _fallback_keyword_search(db: Session, question: str, limit: int) -> list[dict]:
    """LIKE fallback when vectors are unavailable (mock embeddings / empty index)."""
    words = [w for w in question.replace("?", " ").split() if len(w) > 3][:6]
    if not words:
        return []
    is_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
    match_op = "ILIKE" if is_pg else "LIKE"
    conds = " OR ".join([f"content {match_op} :w{i}" for i in range(len(words))])
    params = {f"w{i}": f"%{w}%" for i, w in enumerate(words)}
    enabled = "is_enabled = true" if is_pg else "is_enabled = 1"
    rows = db.execute(
        sql_text(f"""
            SELECT id, document_id, content, standard, subject_name_gu, chapter_name_gu,
                   chapter_number, page_number, section, source, academic_year, source_type,
                   doc_type
            FROM knowledge_chunks
            WHERE {enabled} AND ({conds})
            LIMIT :lim
        """).bindparams(**params),
        {"lim": limit},
    )
    return [dict(r._mapping) for r in rows]


def retrieve_chunks(
    db: Session,
    question: str,
    standard: int | None,
    subject_id: str | None,
    chapter_id: str | None,
    top_k: int = 6,
) -> list[dict]:
    """Vector similarity search with hard filters; falls back to keyword search."""
    cache_key = [question, standard, subject_id, chapter_id, top_k]
    cached = cache_service.cache_get("rag", cache_key)
    if cached is not None:
        return cached

    try:
        is_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
        if not is_pg:
            # SQLite dev DB: skip vector SQL entirely, use keyword search
            results = _fallback_keyword_search(db, question, top_k)
            cache_service.cache_set("rag", cache_key, results, ttl=60 * 30)
            return results

        qvec = embed_query(question)
        vec_literal = "[" + ",".join(f"{x:.6f}" for x in qvec) + "]"

        where = ["c.is_enabled = true", "d.is_enabled = true", "d.status = 'completed'",
                 "c.embedding IS NOT NULL"]
        # Fetch extra candidates, then prefer textbook chunks when trimming.
        params: dict = {"vec": vec_literal, "k": top_k * 2}
        if standard:
            where.append("c.standard = :std")
            params["std"] = standard
        if subject_id:
            where.append("(c.subject_id = :sid OR c.subject_id IS NULL)")
            params["sid"] = subject_id
        if chapter_id:
            where.append("(c.chapter_id = :cid OR c.chapter_id IS NULL)")
            params["cid"] = chapter_id

        # NOTE: never write ":param::type" in text() — SQLAlchemy's parser drops
        # the bind param when a PG cast follows it. Use CAST(:param AS type).
        # halfvec comparison matches the HNSW index (embeddings are 2048-dim,
        # above ivfflat's 2000-dim cap).
        distance_expr = "c.embedding::halfvec(2048) <=> CAST(:vec AS halfvec)"
        sql = sql_text(f"""
            SELECT c.id, c.document_id, c.content, c.standard, c.subject_name_gu,
                   c.chapter_name_gu, c.chapter_number, c.page_number, c.section,
                   c.source, c.academic_year, c.source_type, c.doc_type,
                   {distance_expr} AS distance
            FROM knowledge_chunks c
            JOIN knowledge_documents d ON d.id = c.document_id
            WHERE {' AND '.join(where)}
            ORDER BY {distance_expr}
            LIMIT :k
        """)
        rows = db.execute(sql, params)
        results = [dict(r._mapping) for r in rows]
        for r in results:
            r["distance"] = float(r["distance"]) if r["distance"] is not None else 1.0
        # Re-rank: real textbook chunks get a small bonus over AI-generated notes.
        results.sort(key=lambda r: r["distance"] * (0.9 if r.get("doc_type") == "textbook" else 1.0))
        results = results[:top_k]
    except Exception as exc:
        # The failed statement aborted the session's transaction — roll back
        # before reusing it, or the keyword fallback below fails too.
        db.rollback()
        logger.warning("Vector search failed (%s); using keyword fallback", exc)
        results = _fallback_keyword_search(db, question, top_k)

    if not results:
        results = _fallback_keyword_search(db, question, top_k)

    cache_service.cache_set("rag", cache_key, results, ttl=60 * 30)
    return results


def build_rag_context(chunks: list[dict]) -> tuple[str, list[dict]]:
    """Build the reference-content block and source list for a message."""
    if not chunks:
        return "", []
    parts = ["સંદર્ભ સામગ્રી (Gyan Sathi જ્ઞાન કોશમાંથી):"]
    sources = []
    for i, c in enumerate(chunks, 1):
        header_bits = []
        if c.get("standard"):
            header_bits.append(f"ધોરણ {c['standard']}")
        if c.get("subject_name_gu"):
            header_bits.append(c["subject_name_gu"])
        if c.get("chapter_name_gu"):
            header_bits.append(f"પ્રકરণ: {c['chapter_name_gu']}")
        if c.get("section"):
            header_bits.append(c["section"])
        header = " → ".join(header_bits) or "સંદર્ભ"
        parts.append(f"[{i}] {header}\n{c['content']}")
        sources.append({
            "index": i,
            "standard": c.get("standard"),
            "subject_gu": c.get("subject_name_gu"),
            "chapter_gu": c.get("chapter_name_gu"),
            "chapter_number": c.get("chapter_number"),
            "page_number": c.get("page_number"),
            "section": c.get("section"),
            "source": c.get("source"),
            "academic_year": c.get("academic_year"),
            "source_type": c.get("source_type"),
            "doc_type": c.get("doc_type"),
        })
    return "\n\n".join(parts), sources


def rag_retrieval_score(chunks: list[dict]) -> float:
    """Best distance → rough relevance score (1 - distance, cosine)."""
    if not chunks:
        return 0.0
    d = chunks[0].get("distance")
    if d is None:
        return 0.5
    return max(0.0, min(1.0, 1.0 - float(d)))
