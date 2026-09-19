"""Auth API: email OTP signup (direct SMTP primary; Supabase/dev fallbacks), password login."""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, get_current_user, hash_password, verify_password,
)
from app.models.user import User
from app.schemas import (
    DirectSignupRequest, OnboardingRequest, PasswordLoginRequest,
    ProfileUpdate, SendOTPRequest, SetPasswordRequest, VerifyOTPRequest,
)
from app.services import usage_service
from app.services.otp_service import generate_and_store_otp, send_otp_email, verify_otp

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _rate_ok(email: str) -> bool:
    from app.services import cache_service

    return cache_service.cache_incr("otp_sent", [email.lower()], ttl=600) <= 5


@router.post("/send-otp")
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    """Send a signup/login OTP to the email (direct SMTP → Supabase → dev mode)."""
    if not EMAIL_RE.match(body.email):
        raise HTTPException(400, "માન્ય ઈમેલ આપો.")
    if not _rate_ok(body.email):
        raise HTTPException(429, "ઘણી વિનંતીઓ થઈ. થોડા સમય પછી પ્રયાસ કરો.")

    # 1) Direct SMTP — self-contained, no external auth service needed
    code = generate_and_store_otp(body.email)
    sent = send_otp_email(body.email, code)
    if sent.get("sent"):
        return {"sent": True, "method": "smtp",
                "message": "તમારા ઈમેલ પર OTP મોકલવામાં આવ્યો છે."}

    # 2) Supabase OTP (if configured)
    if settings.supabase_url and settings.supabase_service_role_key:
        from app.services import supabase_service

        result = supabase_service.send_signup_otp(body.email)
        if result.get("sent"):
            return {"sent": True, "method": "supabase",
                    "message": "તમારા ઈમેલ પર OTP મોકલવામાં આવ્યો છે."}

    # 3) Dev fallback — no SMTP/Supabase configured
    if settings.environment == "development" or not settings.smtp_host:
        logger.warning("No SMTP/Supabase — dev OTP mode for %s", body.email)
        return {"sent": True, "dev_mode": True,
                "message": "ડેવ મોડ: SMTP સેટ નથી — OTP 000000 વાપરો."}

    raise HTTPException(502, "OTP મોકલી શકાયો નથી. થોડીવાર પછી પ્રયાસ કરો.")


@router.post("/verify-otp")
def verify_otp_endpoint(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify OTP → create/find student → issue app JWT."""
    email = body.email.lower()
    verified = False

    # 1) Own OTP store (direct SMTP flow)
    res = verify_otp(email, body.otp)
    if res.get("ok"):
        verified = True
    else:
        # 2) Supabase OTP fallback (only when configured)
        if settings.supabase_url and settings.supabase_service_role_key:
            from app.services import supabase_service

            sres = supabase_service.verify_signup_otp(email, body.otp)
            if sres.get("verified"):
                verified = True
            else:
                raise HTTPException(401, res.get("error") or "OTP ખોટો છે અથવા સમાપ્ત થયો છે.")
        else:
            # 3) Dev fallback
            if body.otp == "000000" and settings.environment == "development":
                verified = True
            else:
                raise HTTPException(401, res.get("error") or "OTP ખોટો છે.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name="", role="student", onboarded=False)
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.is_active:
        raise HTTPException(403, "તમારું ખાતું બંધ કરેલું છે. સંપર્ક કરો support@gyansathi.in")

    # Optional password creation at signup — afterwards the student can log in
    # with email+password and OTP stays reserved for account recovery.
    if body.password:
        if len(body.password) < 6:
            raise HTTPException(400, "પાસવર્ડ ઓછામાં ઓછો 6 અક્ષરનો હોવો જોઈએ.")
        user.password_hash = hash_password(body.password)
        db.commit()

    token = create_access_token(user)
    return {
        "access_token": token,
        "user": user.to_dict(),
        "needs_onboarding": not user.onboarded,
    }


@router.post("/signup")
def direct_signup(body: DirectSignupRequest, db: Session = Depends(get_db)):
    """Direct email+password signup — no OTP. OTP stays reserved for
    forgot-password recovery only (per product decision)."""
    email = body.email.lower()
    user = db.query(User).filter(User.email == email).first()
    if user:
        if user.password_hash:
            raise HTTPException(409, "આ ઈમેલ પહેલેથી નોંધાયેલું છે. લોગ ઇન કરો અથવા પાસવર્ડ ભૂલાવો વાપરો.")
        # Pre-existing OTP-only account: claim it by setting a password.
        user.password_hash = hash_password(body.password)
        if body.full_name:
            user.full_name = body.full_name.strip()
        db.commit()
    else:
        user = User(
            email=email,
            full_name=body.full_name.strip(),
            role="admin" if email in settings.admin_email_list else "student",
            onboarded=False,
        )
        user.password_hash = hash_password(body.password)
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.is_active:
        raise HTTPException(403, "તમારું ખાતું બંધ કરેલું છે. સંપર્ક કરો support@gyansathi.in")

    token = create_access_token(user)
    return {
        "access_token": token,
        "user": user.to_dict(),
        "needs_onboarding": not user.onboarded,
    }


@router.post("/login")
def password_login(body: PasswordLoginRequest, db: Session = Depends(get_db)):
    """Email+password login (students who set a password at signup, and admins)."""
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "ઈમેલ અથવા પાસવર્ડ ખોટો છે.")
    if not user.is_active:
        raise HTTPException(403, "ખાતું નિષ્ક્રિય છે.")
    token = create_access_token(user)
    return {"access_token": token, "user": user.to_dict(),
            "needs_onboarding": not user.onboarded}


@router.post("/set-password")
def set_password(body: SetPasswordRequest, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Set/replace the login password for the signed-in account."""
    if len(body.password) < 6:
        raise HTTPException(400, "પાસવર્ડ ઓછામાં ઓછો 6 અક્ષરનો હોવો જોઈએ.")
    user.password_hash = hash_password(body.password)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = user.to_dict()
    data["subscription"] = usage_service.usage_snapshot(db, user.id)["upload"]
    data["is_premium"] = usage_service.is_premium(db, user.id)
    return data


@router.post("/onboarding")
def complete_onboarding(body: OnboardingRequest, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    user.full_name = body.full_name.strip()
    user.standard = body.standard
    user.medium = body.medium
    user.preferred_language = body.preferred_language
    user.onboarded = True
    db.commit()
    return {"ok": True, "user": user.to_dict()}


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    # JWT is stateless; client discards the token. Endpoint kept for API symmetry.
    return {"ok": True}
