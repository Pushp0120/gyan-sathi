"""Fill the remaining textbook chapters: generate GSEB-style content and
import through the live bulk-ingest flow (server-side skip keeps it idempotent).

Usage (from backend/ with DATABASE_URL pointing at the cloud DB):
    python scripts/generate_and_import_textbook.py
"""
import json
import os
import sys
import time
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.knowledge import KnowledgeDocument  # noqa: E402
from app.models.subject import Subject  # noqa: E402
from app.services.ai_service import choose_model, get_ai_provider  # noqa: E402
from seed_syllabus_full import CHAPTERS  # noqa: E402

BASE = "https://gyansathii.vercel.app"
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "textbook_import_state.json")
ADMIN_EMAIL = "admin@gyansathi.in"
ADMIN_PASSWORD = "Admin@123"

PROMPT = (
    "તમે GSEB (ગુજરાત બોર્ડ) ના ધોરણ 10 ના {subject} ({subject_gu}) વિષયના "
    "પાઠ્યપુસ્તકના લેખક છો. પ્રકરણ '{chapter}' નું પાઠ્યપુસ્તક-શૈલીનું મોટું પ્રકરણ "
    "ગુજરાતીમાં લખો (650-950 શબ્દો).\n"
    "માળખું: ## મથાળાં વાપરો; **વ્યાખ્યા/મુખ્ય ખ્યાલ** બોલ્ડમાં; દરેક ખ્યાલ સમજૂતી + "
    "ઉદાહરણ + ગુણોત્તર શૈલીમાં; વ્યાખ્યાઓ પાઠ્યપુસ્તકની ભાષામાં; છેલ્લે "
    "'## પ્રકરણ સાર' (5-7 મુદ્દા) અને '## સ્વાધ્યાય' (4-6 પ્રશ્નો).\n"
    "ફક્ત પ્રકરણનું લખાણ જ લખો — કોઈ પ્રસ્તાવના-મેટા, 'અહીં છે', માર્કડાઉન ટિપ્પણી નહીં."
)


def load_state() -> set:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_state(done: set) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f)


def admin_token() -> str:
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=90))["access_token"]


def upload_chapter(token: str, chapter_id: str, filename: str, content: str) -> dict:
    boundary = uuid.uuid4().hex
    fields = {"chapter_ids": json.dumps([chapter_id]), "standard": "10",
              "doc_type": "textbook", "replace": "true"}
    body = b""
    for k, v in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
             f"filename=\"{filename}\"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n").encode()
    body += content.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + "/api/admin/bulk/ingest", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req, timeout=180))


def textbook_enabled(chapter_id: str) -> bool:
    db = SessionLocal()
    try:
        return db.query(KnowledgeDocument).filter(
            KnowledgeDocument.chapter_id == chapter_id,
            KnowledgeDocument.doc_type == "textbook",
            KnowledgeDocument.is_enabled == True,  # noqa: E712
        ).count() > 0
    finally:
        db.close()


def stored_textbook_text(chapter_id: str) -> str | None:
    db = SessionLocal()
    try:
        doc = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.chapter_id == chapter_id,
            KnowledgeDocument.doc_type == "textbook",
            KnowledgeDocument.is_enabled == True,  # noqa: E712
        ).first()
        return (doc.raw_text or "").strip() if doc else None
    finally:
        db.close()


def main() -> None:
    provider = get_ai_provider()
    model = choose_model("ask")
    print(f"AI provider: {provider.name} | model: {model}", flush=True)
    token = admin_token()
    print("admin login OK", flush=True)

    done = load_state()
    failures: list[tuple] = []
    imported = 0

    for (std, subj_en), chapters in CHAPTERS.items():
        if std != 10:
            continue
        db = SessionLocal()
        subject = db.query(Subject).filter(
            Subject.name_en == subj_en, Subject.standard == 10).first()
        db.close()
        if not subject:
            continue
        for number, name_gu in chapters:
            db = SessionLocal()
            ch = db.query(Chapter).filter(
                Chapter.subject_id == subject.id, Chapter.number == number).first()
            db.close()
            if not ch:
                print(f"?? {subj_en} ch{number}: chapter row missing", flush=True)
                continue
            if ch.id in done or textbook_enabled(ch.id):
                done.add(ch.id)
                save_state(done)
                continue

            # Content: prefer any real textbook text already stored, else AI-generate.
            raw = stored_textbook_text(ch.id)
            if raw and len(raw) > 400:
                content, src = raw, "stored-text"
            else:
                try:
                    result = provider.chat(
                        [{"role": "user", "content": PROMPT.format(
                            subject=subj_en, subject_gu=subject.name_gu, chapter=name_gu)}],
                        model=model, temperature=0.35, max_tokens=2400)
                    content = result["content"] if isinstance(result, dict) else str(result)
                    src = "ai"
                except Exception as exc:
                    msg = str(exc)[:120]
                    print(f"!! {subj_en} ch{number}: generate failed: {msg}", flush=True)
                    failures.append((subj_en, number, "gen: " + msg))
                    time.sleep(20)
                    continue

            fname = f"{subj_en}-CH-{number:02d}.txt"
            try:
                res = upload_chapter(token, ch.id, fname, content)["results"][0]
            except Exception as exc:
                msg = str(exc)[:120]
                print(f"!! {subj_en} ch{number}: upload failed: {msg}", flush=True)
                failures.append((subj_en, number, "up: " + msg))
                time.sleep(10)
                continue

            if res["ok"]:
                imported += 1
                done.add(ch.id)
                save_state(done)
                print(f"✓ {subj_en} ch{number} [{src}] chunks={res['chunks']} "
                      f"retired={res['retired_docs']}", flush=True)
            elif "પહેલેથી" in (res.get("error") or ""):
                done.add(ch.id)  # server says textbook already exists → done
                save_state(done)
                print(f"= {subj_en} ch{number}: already has textbook (skip)", flush=True)
            else:
                print(f"!! {subj_en} ch{number}: {res.get('error')}", flush=True)
                failures.append((subj_en, number, "ingest: " + str(res.get("error"))[:100]))
            time.sleep(1.2)

    # One retry round for transient (rate-limit) failures.
    if failures:
        print(f"\nretry round for {len(failures)} failures after 90s cooldown...", flush=True)
        time.sleep(90)
        retry, failures = list(failures), []
        for subj_en, number, _ in retry:
            db = SessionLocal()
            subject = db.query(Subject).filter(
                Subject.name_en == subj_en, Subject.standard == 10).first()
            ch = db.query(Chapter).filter(
                Chapter.subject_id == subject.id, Chapter.number == number).first()
            db.close()
            if not ch or ch.id in done:
                continue
            try:
                result = provider.chat(
                    [{"role": "user", "content": PROMPT.format(
                        subject=subj_en, subject_gu=subject.name_gu,
                        chapter=ch.name_gu)}],
                    model=model, temperature=0.35, max_tokens=2400)
                content = result["content"] if isinstance(result, dict) else str(result)
                res = upload_chapter(token, ch.id,
                                     f"{subj_en}-CH-{number:02d}.txt", content)["results"][0]
                if res["ok"]:
                    imported += 1
                    done.add(ch.id)
                    save_state(done)
                    print(f"✓ retry {subj_en} ch{number} chunks={res['chunks']}", flush=True)
                    continue
            except Exception as exc:
                print(f"!! retry {subj_en} ch{number}: {str(exc)[:100]}", flush=True)
            failures.append((subj_en, number, "retry"))

    print("\nDONE:", {"imported": imported, "state_size": len(done),
                       "failed": failures}, flush=True)


if __name__ == "__main__":
    main()
