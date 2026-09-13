"""(Re)generate embeddings for knowledge chunks missing vectors.

Usage: python -m scripts.generate_embeddings [--document-id ID]
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import embed_texts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embed")


def main():
    doc_id = None
    if "--document-id" in sys.argv:
        doc_id = sys.argv[sys.argv.index("--document-id") + 1]

    db = SessionLocal()
    try:
        q = db.query(KnowledgeChunk).filter(KnowledgeChunk.embedding.is_(None))
        if doc_id:
            q = q.filter(KnowledgeChunk.document_id == doc_id)
        chunks = q.all()
        logger.info("Chunks needing embeddings: %d", len(chunks))
        batch = 8
        done = 0
        for i in range(0, len(chunks), batch):
            part = chunks[i:i + batch]
            try:
                vecs = embed_texts([c.content for c in part], input_type="passage")
                for c, v in zip(part, vecs):
                    if v:
                        c.embedding = v
                        done += 1
                db.commit()
            except Exception as exc:
                logger.error("batch failed: %s", exc)
                db.rollback()
        logger.info("Embedded %d/%d chunks ✔", done, len(chunks))
    finally:
        db.close()


if __name__ == "__main__":
    main()
