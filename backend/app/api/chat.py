"""Chat API: RAG-powered Gujarati tutor chat with streaming."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.conversation import Conversation, Message
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.user import User
from app.prompts.gujarati_tutor import build_system_prompt, build_user_context
from app.schemas import ChatRequest, FeedbackRequest, ChatTitleRequest
from app.services import cache_service, usage_service
from app.services.ai_service import choose_model, get_ai_provider
from app.utils.text_sanitizer import sanitize_gujarati
from app.services.rag_service import build_rag_context, detect_filters, rag_retrieval_score, retrieve_chunks

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api", tags=["chat"])

MAX_HISTORY_MESSAGES = 10


def _get_owned_conversation(db: Session, user: User, conversation_id: str | None, create: bool = True):
    if not conversation_id:
        if not create:
            return None
        conv = Conversation(student_id=user.id, standard=user.standard, title="નવો સંવાદ")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.student_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "સંવાદ મળ્યો નથી.")
    return conv


def _build_messages(db: Session, user: User, conv: Conversation, body: ChatRequest,
                    context_text: str, sources_note: str) -> tuple[list[dict], str]:
    """Assemble system + history + context + question messages."""
    subject_gu = chapter_gu = None
    if body.subject_id:
        subj = db.query(Subject).get(body.subject_id)
        subject_gu = subj.name_gu if subj else None
    if body.chapter_id:
        chap = db.query(Chapter).get(body.chapter_id)
        chapter_gu = chap.name_gu if chap else None

    standard = user.standard or conv.standard

    sys_prompt = build_system_prompt(body.mode)
    messages = [{"role": "system", "content": sys_prompt}]

    ctx = build_user_context(standard, subject_gu, chapter_gu, user.preferred_language or "gu")
    if context_text:
        ctx += "\n\n" + context_text
    if sources_note:
        ctx += "\n\n" + sources_note
    messages.append({"role": "system", "content": ctx})

    history = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    for m in reversed(history):
        messages.append({"role": "user" if m.role == "user" else "assistant",
                         "content": m.content[:2000]})
    messages.append({"role": "user", "content": body.message})
    return messages, (subject_gu or "")


@router.post("/chat")
def chat(body: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.onboarded:
        raise HTTPException(400, "પહેલા ઑનબોર્ડિંગ પૂર્ણ કરો.")
    if not usage_service.rate_limit_ok("chat", user.id, settings.rate_limit_chat_per_min):
        raise HTTPException(429, "થોડા સમય પછી ફરી પ્રયાસ કરો.")

    conv = _get_owned_conversation(db, user, body.conversation_id)
    standard = user.standard or conv.standard

    # --- RAG retrieval (context + answer cache key)
    filters = detect_filters(body.message, default_standard=standard)
    chunks = retrieve_chunks(db, body.message, filters["standard"],
                             body.subject_id or conv.subject_id, body.chapter_id or conv.chapter_id)
    context_text, sources = build_rag_context(chunks)
    score = rag_retrieval_score(chunks)
    sources_note = (
        "સૂચના: ઉપરની સંદર્ભ સામગ્રી પૂરતી નથી. જો જવાબ આપો તો સ્પષ્ટ લખો કે આ સામાન્ય સમજૂતી છે, "
        "પાઠ્યપુસ્તકમાંથી નથી."
        if score < 0.35 and chunks else
        ("સૂચના: જ્ઞાન કોશમાં આ વિષયની માહિતી ઉપલબ્ધ નથી. સામાન્ય સમજૂતી આપો અને સ્પષ્ટ જણાવો કે તે પાઠ્યપુસ્તક આધારિત નથી."
         if not chunks else "")
    )

    # --- AI answer cache for safe reusable questions
    cache_key = [body.message.lower().strip(), filters["standard"], body.subject_id,
                 body.chapter_id, body.mode, user.preferred_language]
    cached = cache_service.cache_get("ai_answer", cache_key)
    from_cache = False
    if cached is not None:
        answer, sources_out, from_cache, tokens = cached["content"], cached["sources"], True, 0
    else:
        messages, _ = _build_messages(db, user, conv, body, context_text, sources_note)
        provider = get_ai_provider()
        try:
            resp = provider.chat(messages, model=choose_model(body.mode), temperature=0.35,
                                 max_tokens=1800)
        except (TimeoutError, RuntimeError) as exc:
            raise HTTPException(503, str(exc))
        answer, tokens = resp["content"], resp.get("tokens", 0)
        sources_out = sources
        if score >= 0.5 or not chunks:  # cache only stable, well-grounded or general answers
            cache_service.cache_set("ai_answer", cache_key,
                                    {"content": answer, "sources": sources_out})

    # --- persist (sanitize any mixed-script slips before storing)
    answer = sanitize_gujarati(answer)
    user_msg = Message(conversation_id=conv.id, role="user", content=body.message,
                       mode=body.mode)
    ai_msg = Message(conversation_id=conv.id, role="assistant", content=answer,
                     mode=body.mode, sources=sources_out, used_rag=bool(chunks),
                     tokens_used=tokens)
    db.add_all([user_msg, ai_msg])
    if conv.title in ("નવો સંવાદ", ""):
        conv.title = body.message[:42] + ("…" if len(body.message) > 42 else "")
    conv.updated_at = __import__("app.utils.time", fromlist=["utcnow"]).utcnow()
    db.commit()

    # --- progress + usage counters
    usage_service.bump_usage(db, user.id, ai_requests=1, tokens_used=tokens)
    _bump_progress(db, user, conv, body)

    return {
        "conversation_id": conv.id,
        "message_id": ai_msg.id,
        "answer": answer,
        "sources": sources_out,
        "used_rag": bool(chunks),
        "retrieval_score": round(score, 3),
        "from_cache": from_cache,
        "title": conv.title,
    }


def _bump_progress(db: Session, user: User, conv: Conversation, body: ChatRequest) -> None:
    chapter_id = body.chapter_id or conv.chapter_id
    if not chapter_id:
        return
    from app.models.progress import StudentProgress
    from app.utils.time import utcnow

    row = db.query(StudentProgress).filter(
        StudentProgress.student_id == user.id, StudentProgress.chapter_id == chapter_id
    ).first()
    if not row:
        row = StudentProgress(student_id=user.id, chapter_id=chapter_id,
                              standard=user.standard, subject_id=body.subject_id or conv.subject_id)
        db.add(row)
    row.questions_asked = (row.questions_asked or 0) + 1
    row.completion_percent = min(100.0, (row.questions_asked or 0) * 10 +
                                 (row.quiz_attempts or 0) * 15)
    row.last_studied_at = utcnow()
    db.commit()


@router.post("/chat/stream")
def chat_stream(body: ChatRequest, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Streaming chat (SSE-style plain text chunks)."""
    if not user.onboarded:
        raise HTTPException(400, "પહેલા ઑનબોર્ડિંગ પૂર્ણ કરો.")
    if not usage_service.rate_limit_ok("chat", user.id, settings.rate_limit_chat_per_min):
        raise HTTPException(429, "થોડા સમય પછી ફરી પ્રયાસ કરો.")

    conv = _get_owned_conversation(db, user, body.conversation_id)
    standard = user.standard or conv.standard
    filters = detect_filters(body.message, default_standard=standard)
    chunks = retrieve_chunks(db, body.message, filters["standard"],
                             body.subject_id or conv.subject_id, body.chapter_id or conv.chapter_id)
    context_text, sources = build_rag_context(chunks)
    score = rag_retrieval_score(chunks)
    messages, _ = _build_messages(db, user, conv, body, context_text, "")
    model = choose_model(body.mode)

    def gen():
        full = []
        try:
            stream = get_ai_provider().chat(messages, model=model, temperature=0.35,
                                            max_tokens=1800, stream=True)
            for piece in stream:
                piece = sanitize_gujarati(piece)  # per-chunk; mapping is per-codepoint so chunk boundaries are safe
                full.append(piece)
                yield "data: " + json.dumps({"type": "delta", "content": piece},
                                            ensure_ascii=False) + "\n\n"
        except Exception as exc:
            logger.exception("stream failed")
            yield "data: " + json.dumps({"type": "error",
                                         "content": "કંઈક સમસ્યા આવી છે. થોડીવાર પછી ફરી પ્રયાસ કરો."},
                                        ensure_ascii=False) + "\n\n"
        finally:
            answer = sanitize_gujarati("".join(full))
            if answer:
                user_msg = Message(conversation_id=conv.id, role="user", content=body.message,
                                   mode=body.mode)
                ai_msg = Message(conversation_id=conv.id, role="assistant", content=answer,
                                 mode=body.mode, sources=sources, used_rag=bool(chunks))
                db.add_all([user_msg, ai_msg])
                if conv.title in ("નવો સંવાદ", ""):
                    conv.title = body.message[:42] + ("…" if len(body.message) > 42 else "")
                db.commit()
                usage_service.bump_usage(db, user.id, ai_requests=1)
                _bump_progress(db, user, conv, body)
            yield "data: " + json.dumps({
                "type": "done", "conversation_id": conv.id,
                "sources": sources, "used_rag": bool(chunks),
                "retrieval_score": round(score, 3),
            }, ensure_ascii=False) + "\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------- history

@router.get("/chats")
def list_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = (
        db.query(Conversation)
        .filter(Conversation.student_id == user.id, Conversation.is_archived == False)  # noqa: E712
        .order_by(Conversation.updated_at.desc())
        .limit(100)
        .all()
    )
    return {"chats": [c.to_dict() for c in convs]}


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == chat_id, Conversation.student_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "સંવાદ મળ્યો નથી.")
    return conv.to_dict(with_messages=True)


@router.patch("/chats/{chat_id}")
def rename_chat(chat_id: str, body: ChatTitleRequest, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == chat_id, Conversation.student_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "સંવાદ મળ્યો નથી.")
    conv.title = body.title.strip()[:200]
    db.commit()
    return {"ok": True, "title": conv.title}


@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == chat_id, Conversation.student_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "સંવાદ મળ્યો નથી.")
    db.delete(conv)
    db.commit()
    return {"ok": True}


@router.post("/feedback")
def submit_feedback(body: FeedbackRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    msg = (
        db.query(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Message.id == body.message_id, Conversation.student_id == user.id)
        .first()
    )
    if not msg:
        raise HTTPException(404, "સંદેશ મળ્યો નથી.")
    msg.feedback = body.rating
    from app.models.progress import Feedback as FeedbackModel

    fb = FeedbackModel(message_id=msg.id, student_id=user.id, rating=body.rating,
                       comment=body.comment[:1000])
    db.add(fb)
    db.commit()
    return {"ok": True}
