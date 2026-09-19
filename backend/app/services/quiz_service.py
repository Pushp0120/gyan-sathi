"""Quiz generation (AI via RAG context) and scoring."""
import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.quiz import QuizQuestion
from app.services.ai_service import choose_model, get_ai_provider
from app.services.rag_service import build_rag_context, retrieve_chunks
from app.utils.text_sanitizer import sanitize_gujarati

logger = logging.getLogger(__name__)


def _parse_questions(raw: str) -> list[dict]:
    """Robustly parse a JSON array of questions from the model output."""
    raw = raw.strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        raw = m.group(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Quiz parse failed")
        return []
    out = []
    for q in data:
        if not isinstance(q, dict):
            continue
        text = (q.get("question") or "").strip()
        options = [str(o) for o in (q.get("options") or [])][:4]
        answer = str(q.get("answer") or "").strip()
        if not text or not options or not answer:
            continue
        out.append({
            "question": text,
            "options": options,
            "answer": answer,
            "explanation": str(q.get("explanation") or "").strip(),
            "difficulty": q.get("difficulty", "medium"),
        })
    return out


def generate_quiz(db: Session, standard: int, subject_id: str | None,
                  chapter_id: str | None, subject_gu: str, chapter_gu: str,
                  count: int = 5, student_id: str | None = None) -> list[dict]:
    """Generate MCQs grounded in the knowledge base via RAG."""
    chunks = retrieve_chunks(
        db,
        question=f"{subject_gu} {chapter_gu} મહત્વના પ્રશ્નો પ્રશ્નો પરીક્ષા",
        standard=standard,
        subject_id=subject_id,
        chapter_id=chapter_id,
        top_k=8,
    )
    context, _sources = build_rag_context(chunks)

    from app.prompts.gujarati_tutor import build_system_prompt

    sys_prompt = build_system_prompt(
        "quiz",
        extra=f"Generate exactly {count} MCQ questions in Gujarati. Respond ONLY with a JSON array: "
              '[{"question":"...","options":["...","...","...","..."],"answer":"... exactly one option text",'
              '"explanation":"...","difficulty":"easy|medium|hard"}]. '
              "The answer must exactly match one of the options."
    )
    user_parts = [f"ધોરણ: {standard}", f"વિષય: {subject_gu}"]
    if chapter_gu:
        user_parts.append(f"પ્રકરણ: {chapter_gu}")
    if context:
        user_parts.append(context)
    else:
        user_parts.append("(નોંધ: જ્ઞાન કોશમાં આ પ્રકરણની સામગ્રી મર્યાદિત છે; સામાન્ય GSEB અભ્યાસક્રમ પ્રમાણે સરળ પ્રશ્નો બનાવો.)")
    user_parts.append(f"કુલ {count} પ્રશ્નો બનાવો.")

    provider = get_ai_provider()
    resp = provider.chat(
        [{"role": "system", "content": sys_prompt},
         {"role": "user", "content": "\n\n".join(user_parts)}],
        model=choose_model("quiz"),
        temperature=0.4,
        max_tokens=2000,
    )
    questions = _parse_questions(sanitize_gujarati(resp["content"]))[:count]
    if not questions:
        raise RuntimeError("ક્વિઝ બનાવવામાં સમસ્યા આવી. ફરી પ્રયાસ કરો.")

    # Persist for reuse/analytics; attach generated ids so submit can verify server-side
    for q in questions:
        row = QuizQuestion(
            standard=standard, subject_id=subject_id, chapter_id=chapter_id,
            question_type="mcq", question_text=q["question"],
            options=q["options"], correct_answer=q["answer"],
            explanation=q["explanation"], difficulty=q.get("difficulty", "medium"),
            source="ai-generated",
        )
        db.add(row)
        db.flush()
        q["id"] = row.id
    db.commit()
    return questions


def score_attempt(questions: list[dict], answers: list[dict]) -> dict:
    correct = 0
    detailed = []
    qmap = {i: q for i, q in enumerate(questions)}
    for ans in answers:
        idx = ans.get("question_index")
        q = qmap.get(idx)
        if not q:
            continue
        selected = (ans.get("selected") or "").strip()
        right = selected == (q.get("answer") or "").strip()
        if right:
            correct += 1
        detailed.append({
            "question_index": idx,
            "selected": selected,
            "correct": q.get("answer"),
            "is_right": right,
        })
    total = len(questions)
    return {
        "total": total,
        "correct": correct,
        "wrong": total - correct,
        "score_percent": round(correct * 100 / total, 1) if total else 0,
        "details": detailed,
    }
