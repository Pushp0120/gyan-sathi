"""Import documents from a folder into the knowledge base.

Usage:
  python -m scripts.import_documents --dir ../knowledge-base/std10 \
      --standard 10 --subject "Science" [--chapter "પ્રકાશ"] [--source-type curated]
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.chapter import Chapter
from app.models.knowledge import KnowledgeDocument
from app.models.subject import Subject
from app.services.ingestion_service import process_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("import")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--standard", type=int, required=True, choices=[9, 10])
    ap.add_argument("--subject", required=True, help="English subject name (e.g. Science)")
    ap.add_argument("--chapter", default=None, help="Gujarati chapter name (optional)")
    ap.add_argument("--source-type", default="curated",
                    choices=["gseb", "textbook", "question_bank", "curated", "demo"])
    ap.add_argument("--year", default="2026-27")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        subj = db.query(Subject).filter(Subject.standard == args.standard,
                                        Subject.name_en == args.subject).first()
        if not subj:
            logger.error("Subject %r (std %s) not found — seed first", args.subject, args.standard)
            sys.exit(1)
        chap = None
        if args.chapter:
            chap = db.query(Chapter).filter(Chapter.subject_id == subj.id,
                                            Chapter.name_gu == args.chapter).first()

        folder = Path(args.dir)
        files = [p for p in folder.rglob("*") if p.suffix.lower() in
                 (".pdf", ".txt", ".md", ".docx")]
        if not files:
            logger.error("No supported files in %s", folder)
            sys.exit(1)

        for path in files:
            data = path.read_bytes()
            doc = KnowledgeDocument(
                title=path.stem[:300], source_type=args.source_type,
                standard=args.standard, subject_id=subj.id,
                chapter_id=chap.id if chap else None,
                academic_year=args.year, language="gu",
                file_name=path.name, status="pending",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            try:
                n = process_document(db, doc, data, path.suffix.lstrip(".").lower())
                logger.info("✔ %s → %d chunks (status=%s)", path.name, n, doc.status)
            except Exception as exc:
                logger.error("✘ %s → %s", path.name, exc)
    finally:
        db.close()


if __name__ == "__main__":
    main()
