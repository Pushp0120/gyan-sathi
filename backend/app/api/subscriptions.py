"""Plans & subscription API (server-verified payments)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subscription import Payment, Plan
from app.models.user import User
from app.schemas import SubscriptionCreateRequest, SubscriptionVerifyRequest, UpiVerifyRequest
from app.services import usage_service
from app.services.subscription_service import (
    create_order, create_upi_order, upi_order_status, verify_and_activate, verify_upi_and_activate,
)

settings = get_settings()
router = APIRouter(prefix="/api", tags=["subscription"])


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active == True).all()  # noqa: E712
    return {"plans": [p.to_dict() for p in plans]}


@router.post("/subscription/create")
def subscription_create(body: SubscriptionCreateRequest,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.code == body.plan_code, Plan.is_active == True).first()  # noqa: E712
    if not plan:
        raise HTTPException(404, "પ્લાન મળ્યો નથી.")
    # UPI QR is the default flow unless Razorpay live mode is explicitly on.
    # (A stale PAYMENT_MODE=sandbox env var must never silently disable the QR.)
    if settings.upi_qr_payment_enabled and settings.payment_mode != "live":
        return create_upi_order(db, user.id, plan)
    order = create_order(db, user.id, plan)
    return order


@router.get("/subscription/upi/{payment_id}/status")
def subscription_upi_status(payment_id: str,
                            user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    result = upi_order_status(db, user.id, payment_id)
    if not result.get("found"):
        raise HTTPException(404, "પેમેન્ટ રેકોર્ડ મળ્યો નથી.")
    return result


@router.post("/subscription/upi/verify")
def subscription_upi_verify(body: UpiVerifyRequest,
                            user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    result = verify_upi_and_activate(db, user.id, body.payment_id, body.utr)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "ચકાસણી નિષ્ફળ."))
    return result


@router.post("/subscription/verify")
def subscription_verify(body: SubscriptionVerifyRequest,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    result = verify_and_activate(
        db, user.id, body.payment_id,
        gateway_payment_id=body.gateway_payment_id,
        gateway_signature=body.gateway_signature,
        gateway_order_id=body.gateway_order_id,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "ચકાસણી નિષ્ફળ."))
    return result


@router.get("/subscription/status")
def subscription_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = usage_service.active_subscription(db, user.id)
    usage = usage_service.usage_snapshot(db, user.id)
    return {
        "is_premium": bool(sub),
        "subscription": sub.to_dict() if sub else None,
        "usage": usage,
        "payment_mode": settings.payment_mode,
    }
