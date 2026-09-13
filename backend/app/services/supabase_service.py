"""Supabase client for auth (email OTP) and storage uploads."""
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def get_client():
    """Return a Supabase client (lazy). None when not configured."""
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.warning("Supabase not configured (missing URL or service role key)")
        return None
    try:
        from supabase import create_client

        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        return _client
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to init Supabase client: %s", exc)
        return None


def send_signup_otp(email: str) -> dict:
    """Send a 6-digit email OTP via Supabase (uses custom SMTP when configured).

    `create_user=true` allows brand-new emails to receive a signup OTP.
    """
    client = get_client()
    if not client:
        return {"sent": False, "reason": "supabase_not_configured"}
    try:
        res = client.auth.sign_in_with_otp({"email": email, "options": {"create_user": True}})
        return {"sent": True, "data": getattr(res, "model_dump", lambda: {})()}
    except Exception as exc:
        logger.error("send_signup_otp failed: %s", exc)
        return {"sent": False, "reason": str(exc)}


def verify_signup_otp(email: str, token: str) -> dict:
    """Verify an email OTP; returns the Supabase user (creates the auth user)."""
    client = get_client()
    if not client:
        return {"verified": False, "reason": "supabase_not_configured"}
    try:
        res = client.auth.verify_otp({"type": "email", "email": email, "token": token})
        user = getattr(res, "user", None)
        session = getattr(res, "session", None)
        return {
            "verified": user is not None,
            "supabase_user_id": getattr(user, "id", None),
            "session": getattr(session, "model_dump", lambda: None)() if session else None,
        }
    except Exception as exc:
        logger.error("verify_signup_otp failed: %s", exc)
        return {"verified": False, "reason": str(exc)}


def upload_file(bucket: str, path: str, data: bytes, content_type: str) -> dict:
    """Upload bytes to Supabase Storage; returns public URL or error."""
    client = get_client()
    if not client:
        return {"ok": False, "reason": "supabase_not_configured"}
    try:
        client.storage.from_(bucket).upload(
            path, data, {"content-type": content_type, "upsert": "true"}
        )
        public_url = client.storage.from_(bucket).get_public_url(path)
        return {"ok": True, "url": public_url}
    except Exception as exc:
        logger.error("storage upload failed: %s", exc)
        return {"ok": False, "reason": str(exc)}


def delete_file(bucket: str, path: str) -> bool:
    client = get_client()
    if not client:
        return False
    try:
        client.storage.from_(bucket).remove([path])
        return True
    except Exception:
        return False
