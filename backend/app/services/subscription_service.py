"""Subscription & payments: server-side verification only."""
import hashlib
import hmac
import logging
import re
import time
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.subscription import Payment, Plan, Subscription
from app.services import usage_service
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
settings = get_settings()


def create_order(db: Session, student_id: str, plan: Plan) -> dict:
    """Create a payment order. Uses Razorpay when configured, else sandbox."""
    if settings.razorpay_key_id and settings.razorpay_key_secret and settings.payment_mode == "live":
        try:
            import razorpay

            client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
            order = client.order.create({
                "amount": plan.price_inr * 100,  # paise
                "currency": "INR",
                "receipt": f"gs_{uuid.uuid4().hex[:12]}",
                "notes": {"student_id": student_id, "plan": plan.code},
            })
            payment = Payment(
                student_id=student_id, plan_id=plan.id,
                gateway="razorpay", gateway_order_id=order["id"],
                amount_inr=plan.price_inr, status="created", mode="live",
            )
            db.add(payment)
            db.commit()
            return {
                "payment_id": payment.id, "order_id": order["id"],
                "amount": plan.price_inr, "key_id": settings.razorpay_key_id,
                "mode": "live", "gateway": "razorpay",
            }
        except Exception as exc:
            logger.error("Razorpay order failed: %s", exc)
            raise RuntimeError("પેમેન્ટ શરૂ કરી શકાયું નથી. થોડીવાર પછી પ્રયાસ કરો.")

    # ---- sandbox (development/test): fake order, no gateway call
    payment = Payment(
        student_id=student_id, plan_id=plan.id,
        gateway="sandbox", gateway_order_id=f"sandbox_{uuid.uuid4().hex[:12]}",
        amount_inr=plan.price_inr, status="created", mode="sandbox",
    )
    db.add(payment)
    db.commit()
    return {
        "payment_id": payment.id, "order_id": payment.gateway_order_id,
        "amount": plan.price_inr, "mode": "sandbox", "gateway": "sandbox",
    }


def verify_and_activate(db: Session, student_id: str, payment_id: str,
                        gateway_payment_id: str, gateway_signature: str,
                        gateway_order_id: str = "") -> dict:
    """Verify payment server-side, then activate Premium. NEVER trust the client."""
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.student_id == student_id)
        .first()
    )
    if not payment:
        return {"ok": False, "error": "પેમેન્ટ રેકોર્ડ મળ્યો નથી."}
    if payment.status == "paid":
        return {"ok": True, "already_paid": True, "subscription": _latest_sub_dict(db, student_id)}

    if payment.mode == "live":
        expected = hmac.new(
            settings.razorpay_key_secret.encode(),
            f"{gateway_order_id}|{gateway_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, gateway_signature or ""):
            payment.status = "failed"
            db.commit()
            logger.warning("Signature mismatch for payment %s", payment.id)
            return {"ok": False, "error": "પેમેન્ટ ચકાસણી નિષ્ફળ ગઈ."}
        if gateway_order_id and gateway_order_id != payment.gateway_order_id:
            return {"ok": False, "error": "ઓર્ડર મેળ ખાતો નથી."}
    else:
        # Sandbox mode: any non-empty token activates (test flow only)
        if not gateway_payment_id:
            return {"ok": False, "error": "પેમેન્ટ ટોકન ગુમ થયો છે."}

    plan = db.query(Plan).get(payment.plan_id) if payment.plan_id else None
    if not plan:
        return {"ok": False, "error": "પ્લાન મળ્યો નથી."}

    now = utcnow()
    existing = (
        db.query(Subscription)
        .filter(Subscription.student_id == student_id, Subscription.status == "active")
        .order_by(Subscription.expires_at.desc().nullslast())
        .first()
    )
    base = now
    if existing and existing.is_premium():
        base = existing.expires_at or now  # extend current premium
    expires = base + timedelta_days(plan.duration_days)

    sub = Subscription(
        student_id=student_id, plan_id=plan.id, status="active",
        started_at=now, expires_at=expires,
    )
    db.add(sub)
    payment.status = "paid"
    payment.gateway_payment_id = gateway_payment_id
    payment.gateway_signature = gateway_signature
    payment.paid_at = now
    # Expire older active subs
    for s in db.query(Subscription).filter(
        Subscription.student_id == student_id, Subscription.status == "active"
    ).all():
        if s.id != sub.id and s.expires_at and s.expires_at < expires:
            s.status = "expired"
    db.commit()
    return {"ok": True, "subscription": _latest_sub_dict(db, student_id)}


# ----------------------------------------------------------------- UPI QR flow

UPI_WINDOW_MIN = settings.upi_payment_window_min


def create_upi_order(db: Session, student_id: str, plan: Plan) -> dict:
    """Create a manual UPI-QR payment order, payable for a limited window."""
    if not settings.upi_qr_payment_enabled:
        raise RuntimeError("પેમેન્ટ હાલમાં ઉપલબ્ધ નથી.")
    now = utcnow()
    payment = Payment(
        student_id=student_id,
        plan_id=plan.id,
        gateway="upi_qr",
        gateway_order_id=f"upi_{uuid.uuid4().hex[:12]}",
        amount_inr=plan.price_inr,
        status="created",
        mode="upi_qr",
        notes={"expires_at": (now + timedelta_days(0, minutes=UPI_WINDOW_MIN)).isoformat()},
        # note: UPI window stored in notes so the 2-minute limit is enforced server-side
    )
    db.add(payment)
    db.commit()
    return {
        "payment_id": payment.id,
        "order_id": payment.gateway_order_id,
        "amount": plan.price_inr,
        "payee_name": settings.upi_payee_name,
        "window_seconds": UPI_WINDOW_MIN * 60,
        "expires_at": payment.notes["expires_at"],
        "mode": "upi_qr",
        "gateway": "upi_qr",
    }


def _order_expiry(payment: Payment):
    raw = (payment.notes or {}).get("expires_at")
    if not raw:
        return None
    from datetime import datetime, timezone

    exp = datetime.fromisoformat(raw)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp


def upi_order_status(db: Session, student_id: str, payment_id: str) -> dict:
    """Poll target for the QR window: status + remaining seconds."""
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.student_id == student_id)
        .first()
    )
    if not payment:
        return {"found": False}
    exp = _order_expiry(payment)
    now = utcnow()
    remaining = max(0, int((exp - now).total_seconds())) if exp else 0
    return {
        "found": True,
        "status": payment.status,  # created | paid | failed | expired
        "remaining_seconds": remaining,
        "amount": payment.amount_inr,
    }


def expire_stale_upi_orders(db: Session) -> None:
    """Mark created UPI orders past their window as expired."""
    now = utcnow()
    for p in db.query(Payment).filter(Payment.gateway == "upi_qr", Payment.status == "created").all():
        exp = _order_expiry(p)
        if exp and exp < now:
            p.status = "expired"
    db.commit()


def verify_upi_and_activate(db: Session, student_id: str, payment_id: str, utr: str) -> dict:
    """Verify the UPI reference number (UTR) and activate Premium.

    A UTR is a 12-digit numeric reference every successful UPI credit
    generates. We validate the format and uniqueness (one activation per
    UTR), stay inside the payment window, then activate. Admin can later
    cross-check the UTR against the bank statement — payment.notes keeps
    the audit trail.
    """
    expire_stale_upi_orders(db)

    utr = (utr or "").strip()
    if not re.fullmatch(r"\d{12}", utr):
        return {"ok": False, "error": "UTR 12 અંકનો હોવો જોઈએ (UPI રેફરન્સ નંબર)."}

    # One premium activation per UTR
    dup = (
        db.query(Payment)
        .filter(Payment.gateway == "upi_qr", Payment.status == "paid", Payment.gateway_payment_id == utr)
        .first()
    )
    if dup:
        return {"ok": False, "error": "આ UTR પહેલેથી વપરાયો છે."}

    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.student_id == student_id)
        .first()
    )
    if not payment:
        return {"ok": False, "error": "પેમેન્ટ રેકોર્ડ મળ્યો નથી."}
    if payment.status == "paid":
        return {"ok": True, "already_paid": True, "subscription": _latest_sub_dict(db, student_id)}
    if payment.status == "expired":
        return {"ok": False, "error": "પેમેન્ટ સમય સમાપ્ત થયો. ફરી શરૂ કરો."}

    exp = _order_expiry(payment)
    if exp and exp < utcnow():
        payment.status = "expired"
        db.commit()
        return {"ok": False, "error": "પેમેન્ટ સમય સમાપ્ત થયો. ફરી શરૂ કરો."}

    plan = db.query(Plan).get(payment.plan_id) if payment.plan_id else None
    if not plan:
        return {"ok": False, "error": "પ્લાન મળ્યો નથી."}

    now = utcnow()
    existing = (
        db.query(Subscription)
        .filter(Subscription.student_id == student_id, Subscription.status == "active")
        .order_by(Subscription.expires_at.desc().nullslast())
        .first()
    )
    base = existing.expires_at if existing and existing.is_premium() and existing.expires_at else now
    expires = base + timedelta_days(plan.duration_days)

    sub = Subscription(
        student_id=student_id, plan_id=plan.id, status="active", started_at=now, expires_at=expires
    )
    db.add(sub)
    payment.status = "paid"
    payment.gateway_payment_id = utr
    payment.paid_at = now
    payment.notes = {**(payment.notes or {}), "utr": utr, "verified": "utr-format+uniqueness"}
    for s in db.query(Subscription).filter(
        Subscription.student_id == student_id, Subscription.status == "active"
    ).all():
        if s.id != sub.id and s.expires_at and s.expires_at < expires:
            s.status = "expired"
    db.commit()
    logger.info("UPI payment %s activated for student %s (UTR %s)", payment.id, student_id, utr)
    return {"ok": True, "subscription": _latest_sub_dict(db, student_id)}


def timedelta_days(n: int, minutes: int = 0):
    from datetime import timedelta

    return timedelta(days=n, minutes=minutes)


def _latest_sub_dict(db: Session, student_id: str) -> dict | None:
    sub = usage_service.active_subscription(db, student_id)
    return sub.to_dict() if sub else None
