"""Plans & subscription API (server-verified payments)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subscription import Payment, Plan
from app.models.user import User
from app.schemas import SubscriptionCreateRequest, SubscriptionVerifyRequest
from app.services import usage_service
from app.services.subscription_service import create_order, verify_and_activate

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
    order = create_order(db, user.id, plan)
    return order


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
