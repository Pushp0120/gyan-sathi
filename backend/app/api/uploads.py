"""Uploads API: file validation, allowance enforcement, text extraction, AI analysis."""
import logging
import os
import re
import secrets
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.upload import Upload
from app.models.user import User
from app.services import supabase_service, usage_service
from app.services.usage_service import bump_usage

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api", tags=["uploads"])

BLOCKED_EXT = {"exe", "bat", "sh", "js", "php", "py", "cmd", "com", "scr", "msi", "dll"}


def _safe_filename(original: str) -> str:
    base = os.path.basename(original or "file")
    base = re.sub(r"[^A-Za-z0-9._\- GujaratiBha]", "", base)
    name, ext = os.path.splitext(base)
    ext = ext.lower().lstrip(".")
    return f"{secrets.token_hex(8)}_{name[:60]}.{ext if ext else 'bin'}"


@router.post("/uploads")
def create_upload(
    file: UploadFile = File(...),
    conversation_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ---- validate type
    original = file.filename or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in settings.allowed_types_list or ext in BLOCKED_EXT:
        raise HTTPException(400, "આ ફાઇલ પ્રકાર માન્ય નથી. PDF, DOCX, TXT, MD અથવા ઇમેજ અપલોડ કરો.")

    data = file.file.read()
    if len(data) == 0:
        raise HTTPException(400, "ખાલી ફાઇલ.")
    if len(data) > settings.upload_max_size:
        raise HTTPException(413, "ફાઇલ ખૂબ મોટી છે (મહત્તમ 10MB).")

    # ---- server-side allowance check (never trust client)
    check = usage_service.upload_check(db, user.id)
    if not check["can_upload"]:
        raise HTTPException(402, "તમારા 10 મફત uploads પૂર્ણ થઈ ગયા છે. Premium મેળવો.")

    file_type = "image" if ext in ("png", "jpg", "jpeg") else ext
    safe_name = _safe_filename(original)

    # ---- store (Supabase Storage if configured, else local disk)
    stored_path = ""
    storage_url = ""
    os.makedirs(settings.upload_dir, exist_ok=True)
    local_path = os.path.join(settings.upload_dir, f"{uuid.uuid4().hex[:8]}_{safe_name}")
    with open(local_path, "wb") as f:
        f.write(data)
    stored_path = local_path

    if settings.supabase_url and settings.supabase_service_role_key:
        object_path = f"{user.id}/{safe_name}"
        up = supabase_service.upload_file("uploads", object_path, data,
                                          file.content_type or "application/octet-stream")
        if up.get("ok"):
            storage_url = up.get("url", "")

    # ---- extract text for AI analysis (images stored but not OCR'd yet)
    extracted = ""
    status = "completed"
    if file_type in ("pdf", "docx", "txt", "md"):
        try:
            from app.services.ingestion_service import extract_text

            extracted = extract_text(data, "docx" if file_type == "docx" else file_type)
            extracted = extracted.replace("[[page:", "[page:")[:20000]
        except Exception as exc:
            status = "failed"
            logger.warning("extract failed: %s", exc)

    upload = Upload(
        student_id=user.id,
        conversation_id=conversation_id,
        original_name=original[:300],
        stored_path=stored_path,
        storage_url=storage_url,
        storage_bucket="uploads",
        storage_object=f"{user.id}/{safe_name}" if storage_url else "",
        mime_type=file.content_type or "",
        file_size=len(data),
        file_type=file_type,
        extracted_text=extracted,
        analysis_status=status,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    # ---- consume allowance ONLY on success (audit snapshot)
    upload.uploads_used_after = usage_service.uploads_used(db, user.id)
    db.commit()
    bump_usage(db, user.id, uploads=1)

    return {
        "ok": True,
        "upload": upload.to_dict(),
        "allowance": usage_service.upload_check(db, user.id),
    }


@router.get("/uploads")
def list_uploads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Upload)
        .filter(Upload.student_id == user.id, Upload.is_deleted == False)  # noqa: E712
        .order_by(Upload.created_at.desc())
        .limit(100)
        .all()
    )
    return {"uploads": [r.to_dict() for r in rows],
            "allowance": usage_service.upload_check(db, user.id)}


@router.delete("/uploads/{upload_id}")
def delete_upload(upload_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    row = db.query(Upload).filter(Upload.id == upload_id,
                                  Upload.student_id == user.id).first()
    if not row:
        raise HTTPException(404, "અપલોડ મળ્યો નથી.")
    # NOTE: deleting does NOT restore the free allowance (usage-based).
    row.is_deleted = True
    db.commit()
    if row.storage_object:
        supabase_service.delete_file(row.storage_bucket, row.storage_object)
    return {"ok": True, "note": "ડિલીટ કર્યા પછી મફત મર્યાદા પરત મળતી નથી.",
            "allowance": usage_service.upload_check(db, user.id)}
