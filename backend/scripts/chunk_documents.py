"""Preview semantic chunking for a document (no DB writes).

Usage: python -m scripts.chunk_documents path/to/file.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ingestion_service import clean_text, semantic_chunks, split_with_pages

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.chunk_documents <file>")
        sys.exit(1)
    raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    cleaned = clean_text(raw)
    total = 0
    for seg, page in split_with_pages(cleaned):
        for ch in semantic_chunks(seg):
            total += 1
            preview = ch["content"][:80].replace("\n", " ")
            print(f"[page={page}] [{ch['section'][:30]}] ({len(ch['content'])} chars) {preview}…")
    print(f"\nTotal chunks: {total}")
