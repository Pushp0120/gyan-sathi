"""Seed the FULL GSEB Std 9/10 syllabus into the knowledge base.

Idempotent — safe to rerun:
- Adds missing chapter rows (existing ones are left untouched).
- For every chapter without a knowledge document yet, generates Gujarati
  study notes via the configured AI provider and ingests them (chunk+embed).
- Subjects without a fixed chapter list (languages, ICT, Std 9 Social
  Science) get one "syllabus + key topics" overview document instead.

Usage:  DATABASE_URL=postgresql://... python -m scripts.seed_syllabus_full [9|10]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.knowledge import KnowledgeDocument  # noqa: E402
from app.models.subject import Subject  # noqa: E402
from app.services import ingestion_service  # noqa: E402
from app.services.ai_service import get_ai_provider  # noqa: E402

# ---- Complete chapter lists (GSEB/NCERT Gujarati-medium numbering) ----------

CHAPTERS = {
    (9, "Mathematics"): [
        (1, "સંખ્યા પદ્ધતિ"), (2, "બહુપદી"), (3, "યામ ભૂમિતિ"),
        (4, "બે ચલોમાં રેખીય સમીકરણ"), (5, "યુક્લિડની ભૂમિતિનો પરિચય"),
        (6, "રેખાઓ અને ખૂણા"), (7, "ત્રિકોણ"), (8, "ચતુર્ભુજ"),
        (9, "સમાંતરબાજુ ચતુર્ભુજના ક્ષેત્રફળ"), (10, "વર્તુળ"),
        (11, "રચનાઓ"), (12, "હેરોનનું સૂત્ર"), (13, "પૃષ્ઠફળ અને ઘનફળ"),
        (14, "સંખ્યાશાસ્ત્ર"), (15, "સંભાવના"),
    ],
    (9, "Science"): [
        (1, "આપણી આસપાસનો પદાર્થ"), (2, "પદાર્થ શું છે? ક્ષાર છે?"),
        (3, "પરમાણુ અને અણુ"), (4, "અણુની રચના"),
        (5, "જીવનનું મૂળભૂત એકમ"), (6, "પેશીઓ"),
        (7, "જીવતા સજીવોની વિવિધતા"), (8, "ગતિ"),
        (9, "બળ અને ગતિના નિયમો"), (10, "ગુરુત્વાકર્ષણ"),
        (11, "કાર્ય અને ઊર્જા"), (12, "ધ્વનિ"),
    ],
    (10, "Mathematics"): [
        (1, "વાસ્તવિક સંખ્યાઓ"), (2, "બહુપદી"), (3, "યુગ્મ રેખીય સમીકરણ"),
        (4, "દ્વિઘાત સમીકરણ"), (5, "સમાંતર શ્રેણી"), (6, "ત્રિભુજ"),
        (7, "યામ ભૂમિતિ"), (8, "ત્રિકોણમિતિનો પરિચય"),
        (9, "ત્રિકોણમિતિનાં ઉપયોગો"), (10, "વર્તુળ"), (11, "રચનાઓ"),
        (12, "વર્તુળને સંબંધિત ક્ષેત્રફળ"), (13, "પૃષ્ઠક્ષેત્ર અને ઘનફળ"),
        (14, "સંખ્યાશાસ્ત્ર"), (15, "સંભાવના"),
    ],
    (10, "Science"): [
        (1, "રાસાયણિક પ્રક્રિયાઓ અને સમીકરણો"), (2, "એસિડ, બેઝ અને ક્ષાર"),
        (3, "ધાતુ અને અધાતુ"), (4, "કાર્બન અને તેનાં સંયોજનો"),
        (5, "તત્વોનું આવર્ત વર્ગીકરણ"), (6, "જીવન પ્રક્રિયાઓ"),
        (7, "નિયંત્રણ અને સંકલન"), (8, "સજીવો પ્રજનન કેવી રીતે કરે છે"),
        (9, "આનુવંશિકતા અને ઉત્ક્રાંતિ"),
        (10, "પ્રકાશ – પરાવર્તન અને વક્રીભવન"),
        (11, "માનવ નેત્ર તથા વર્ણવિક્ષેપણ"),
        (12, "વિદ્યુત પ્રવાહનાં મૂળભૂત ખ્યાલો"),
        (13, "ચુંબકીય અસરો અને વિદ્યુત પ્રવાહ"),
        (14, "ઊર્જાના સ્ત્રોતો"), (15, "આપણું પર્યાવરણ"),
        (16, "કુદરતી સંપત્તિનું સંરક્ષણ"),
    ],
    # Geography chapters of GSEB Std 10 Social Science not yet in the DB.
    # (History/Civics numbering varies by edition — add via admin if needed.)
    (10, "Social Science"): [
        (1, "ભારતના સંસાધનો"),
        (2, "જંગલ અને વન્યજીવ સંસાધન"), (3, "જળ સંસાધન"), (4, "કૃષિ"),
        (5, "ખનીજ સંસાધન"), (6, "ઊર્જાના સ્ત્રોત"),
        (7, "પર્યટન વ્યવસાય"), (8, "ઉદ્યોગો"),
        (9, "પરિવહન અને સંદેશાવ્યવહાર"),
    ],
}

# Subjects that get one overview document instead of chapter-wise notes
OVERVIEW_ONLY = {
    "Gujarati": "ગુજરાતી (ગદ્ય, પદ્ય, વ્યાકરણ — પાઠ્યક્રમ અને પરીક્ષા માર્ગદર્શન)",
    "Hindi": "હિન્દી (ગદ્ય, પદ્ય, વ્યાકરણ — પાઠ્યક્રમ અને પરીક્ષા માર્ગદર્શન)",
    "English": "English (Prose, Poetry, Grammar — syllabus and exam guidance)",
    "Sanskrit": "સંસ્કૃત (પાઠ, શબ્દરૂપ, ધાતુરૂપ — પાઠ્યક્રમ માર્ગદર્શન)",
    "ICT": "કમ્પ્યુટર (ICT) — પાઠ્યક્રમના મુખ્ય ખ્યાલો",
    "Social Science (Std 9)": "સામાજિક વિજ્ઞાન ધોરણ 9 (ભૂગોળ, ઇતિહાસ, રાજ્યશાસ્ત્ર, અર્થશાસ્ત્ર — મુખ્ય ખ્યાલો)",
}

NOTES_PROMPT = (
    "તમે GSEB (ગુજરાત બોર્ડ) ના અનુભવી શિક્ષક છો. ધોરણ {std} ના {subject} વિષયના "
    "પ્રકરણ '{chapter}' માટે વિદ્યાર્થીઓ માટે અભ્યાસ નોંધ ગુજરાતીમાં લખો.\n"
    "માળખું: પ્રકરણનો પરિચય, મુખ્ય ખ્યાલો/વ્યાખ્યાઓ (મથાળાં સાથે), "
    "{formulas}, મહત્વના ઉદાહરણો, પરીક્ષાલક્ષી મહત્વના પ્રશ્નો (3-5).\n"
    "સરળ, ધોરણ 9-10 ના વિદ્યાર્થીને અનુકૂળ ગુજરાતી. 350-550 શબ્દ. "
    "ફક્ત નોંધ લખો, કોઈ પ્રસ્તાવના/ઉપસંહાર નહીં."
)

OVERVIEW_PROMPT = (
    "તમે GSEB (ગુજરાત બોર્ડ) ના અનુભવી શિક્ષક છો. ધોરણ {std} ના {subject} વિષય માટે "
    "અભ્યાસ માર્ગદર્શન ગુજરાતીમાં લખો: પાઠ્યક્રમના મુખ્ય વિભાગો, દરેક વિભાગના મુખ્ય ખ્યાલો, "
    "વ્યાકરણ/સૂત્ર/નકશા જેવી મહત્વની બાબતો, અને પરીક્ષા માટે ટીપ્સ. "
    "સરળ ગુજરાતી, મથાળાં સાથે, 350-550 શબ્દ."
)


def get_or_make_chapter(db, subject: Subject, number: int, name_gu: str) -> Chapter:
    ch = (db.query(Chapter)
          .filter(Chapter.subject_id == subject.id, Chapter.number == number)
          .first())
    if ch:
        return ch
    ch = Chapter(subject_id=subject.id, number=number, name_gu=name_gu,
                 name_en="", description="", is_active=True)
    db.add(ch)
    db.commit()
    db.refresh(ch)
    print(f"  + chapter added: {number}. {name_gu}")
    return ch


def doc_exists(db, chapter_id: str) -> bool:
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.chapter_id == chapter_id).count() > 0


def generate_notes(std: int, subject_en: str, chapter: str, subject_gu: str) -> str:
    is_math = "Math" in subject_en or "ગણિત" in subject_gu
    prompt = NOTES_PROMPT.format(
        std=std, subject=subject_gu, chapter=chapter,
        formulas="જરૂરી સૂત્રો/નિયમો" if is_math else "મહત્વની વ્યાખ્યાઓ/નિયમો",
    )
    provider = get_ai_provider()
    resp = provider.chat(
        [{"role": "system", "content": "તમે GSEB ના વિદ્યાર્થી-મૈત્રીપૂર્ણ શિક્ષક છો."},
         {"role": "user", "content": prompt}],
        temperature=0.4, max_tokens=1400,
    )
    return resp["content"]


def generate_overview(std: int, subject_gu: str) -> str:
    provider = get_ai_provider()
    resp = provider.chat(
        [{"role": "system", "content": "તમે GSEB ના વિદ્યાર્થી-મૈત્રીપૂર્ણ શિક્ષક છો."},
         {"role": "user", "content": OVERVIEW_PROMPT.format(std=std, subject=subject_gu)}],
        temperature=0.4, max_tokens=1400,
    )
    return resp["content"]


def ingest(db, title: str, text: str, subject: Subject, chapter: Chapter | None, std: int) -> bool:
    doc = KnowledgeDocument(
        title=title, source_type="curated", standard=std,
        subject_id=subject.id, chapter_id=chapter.id if chapter else None,
        file_name="", status="pending", language="gu",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    try:
        ingestion_service.process_text(db, doc, text)
        return True
    except Exception as exc:
        print(f"    !! ingest failed: {str(exc)[:120]}")
        return False


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    provider_test = get_ai_provider()
    print(f"AI provider: {provider_test.name} | filter: std={only or 'all'}", flush=True)

    stats = {"chapters_added": 0, "docs_created": 0, "skipped": 0, "failed": 0}
    subjects = SessionLocal().query(Subject).all()

    for subject in subjects:
        std = subject.standard
        if only and str(std) != only:
            continue
        # Fresh session per subject; a dropped Neon connection only costs one subject.
        db = SessionLocal()
        subject = db.merge(subject)

        try:
            key = (std, subject.name_en)
            if key in CHAPTERS:
                print(f"[{std}] {subject.name_en}: chapter-wise notes", flush=True)
                for number, name_gu in CHAPTERS[key]:
                    ch = get_or_make_chapter(db, subject, number, name_gu)
                    if doc_exists(db, ch.id):
                        stats["skipped"] += 1
                        continue
                    try:
                        notes = generate_notes(std, subject.name_en, name_gu, subject.name_gu)
                        ok = ingest(db, f"{subject.name_gu} ધોરણ {std} — પ્રકરણ {number}: {name_gu}",
                                    notes, subject, ch, std)
                    except Exception as exc:
                        print(f"    !! {name_gu}: {str(exc)[:140]}", flush=True)
                        stats["failed"] += 1
                        db = SessionLocal()  # fresh session after any failure
                        subject = db.merge(subject)
                        continue
                    stats["docs_created" if ok else "failed"] += ok if ok else 1
                    print(f"    ✓ {number}. {name_gu}", flush=True)
                    time.sleep(0.4)
            else:
                ov_key = (f"{subject.name_en} (Std 9)"
                          if std == 9 and subject.name_en == "Social Science" else subject.name_en)
                if not OVERVIEW_ONLY.get(ov_key):
                    continue
                print(f"[{std}] {subject.name_en}: overview doc", flush=True)
                has_doc = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.subject_id == subject.id).count() > 0
                if has_doc:
                    stats["skipped"] += 1
                else:
                    try:
                        notes = generate_overview(std, subject.name_gu)
                        ok = ingest(db, f"{subject.name_gu} ધોરણ {std} — અભ્યાસ માર્ગદર્શન",
                                    notes, subject, None, std)
                        stats["docs_created" if ok else "failed"] += ok if ok else 1
                        print("    ✓ overview", flush=True)
                    except Exception as exc:
                        print(f"    !! failed: {str(exc)[:140]}", flush=True)
                        stats["failed"] += 1
        finally:
            db.close()

    print("\nDONE:", stats, flush=True)


if __name__ == "__main__":
    main()
