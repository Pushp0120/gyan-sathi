"""Subscription & payments: server-side verification only."""
import hashlib
import hmac
import logging
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


def timedelta_days(n: int):
    from datetime import timedelta

    return timedelta(days=n)


def _latest_sub_dict(db: Session, student_id: str) -> dict | None:
    sub = usage_service.active_subscription(db, student_id)
    return sub.to_dict() if sub else None
