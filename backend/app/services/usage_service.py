"""Usage tracking + upload allowance (server-side source of truth)."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.subscription import Plan, Subscription, Usage
from app.models.upload import Upload
from app.services import cache_service

settings = get_settings()


# ------------------------------------------------------------------ plans

def get_plan(db: Session, code: str) -> Plan | None:
    return db.query(Plan).filter(Plan.code == code).first()


def active_subscription(db: Session, student_id: str) -> Subscription | None:
    subs = (
        db.query(Subscription)
        .filter(Subscription.student_id == student_id, Subscription.status == "active")
        .order_by(Subscription.expires_at.desc().nullslast())
        .all()
    )
    for s in subs:
        if s.is_premium():
            return s
    return None


def is_premium(db: Session, student_id: str) -> bool:
    return active_subscription(db, student_id) is not None


def upload_limit_for(db: Session, student_id: str) -> int:
    """Server-side upload allowance for this student (-1 = unlimited)."""
    sub = active_subscription(db, student_id)
    if sub and sub.plan:
        return sub.plan.upload_limit
    free = get_plan(db, "free")
    return free.upload_limit if free else settings.free_upload_limit


def uploads_used(db: Session, student_id: str) -> int:
    """Usage-based count: successful uploads are never decremented on delete."""
    return (
        db.query(Upload)
        .filter(Upload.student_id == student_id, Upload.is_deleted == False)  # noqa: E712
        .count()
    )


def upload_check(db: Session, student_id: str) -> dict:
    limit = upload_limit_for(db, student_id)
    used = uploads_used(db, student_id)
    remaining = max(0, limit - used) if limit >= 0 else None
    return {
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "can_upload": remaining is None or remaining > 0,
        "is_premium": is_premium(db, student_id),
    }


# ------------------------------------------------------- daily usage (DB)

def bump_usage(db: Session, student_id: str, **fields) -> None:
    """Increment today's usage row (ai_requests/uploads/quiz_generations/tokens_used)."""
    today = date.today()
    row = (
        db.query(Usage)
        .filter(Usage.student_id == student_id, Usage.usage_date == today)
        .first()
    )
    if not row:
        row = Usage(student_id=student_id, usage_date=today)
        db.add(row)
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, (getattr(row, k) or 0) + v)
    db.commit()


def usage_snapshot(db: Session, student_id: str) -> dict:
    today = date.today()
    row = (
        db.query(Usage)
        .filter(Usage.student_id == student_id, Usage.usage_date == today)
        .first()
    )
    daily = row.to_dict() if row else {
        "date": today.isoformat(), "ai_requests": 0, "uploads": 0,
        "quiz_generations": 0, "tokens_used": 0,
    }
    monthly = (
        db.query(
            func_coalesce_sum_ai(), func_coalesce_sum_tokens(),
        )
        .filter(Usage.student_id == student_id)
        .first()
    )
    return {
        "daily": daily,
        "monthly": {
            "ai_requests": int(monthly[0] or 0),
            "tokens_used": int(monthly[1] or 0),
        },
        "upload": upload_check(db, student_id),
    }


def func_coalesce_sum_ai():
    from sqlalchemy import func

    return func.coalesce(func.sum(Usage.ai_requests), 0)


def func_coalesce_sum_tokens():
    from sqlalchemy import func

    return func.coalesce(func.sum(Usage.tokens_used), 0)


# ----------------------------------------------------------- rate limiting

def rate_limit_ok(bucket: str, ident: str, limit: int, window: int = 60) -> bool:
    val = cache_service.cache_incr(bucket, [ident], ttl=window)
    return val <= limit
