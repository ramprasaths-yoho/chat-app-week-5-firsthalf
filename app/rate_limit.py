import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import ApiUsage, utcnow


def as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check_and_record(db: Session, owner: str, session_id) -> ApiUsage:
    """Database-backed rolling-window limiter: N accepted chats per key per hour.
    Raises 429 + Retry-After, otherwise records this request and returns its row."""
    now = utcnow()
    window = timedelta(seconds=config.RATE_LIMIT_WINDOW_SECONDS)
    stamps = [
        as_utc(t)
        for t in db.scalars(
            select(ApiUsage.created_at)
            .where(ApiUsage.api_key_hash == owner, ApiUsage.created_at >= now - window)
            .order_by(ApiUsage.created_at)
        )
    ]
    if len(stamps) >= config.RATE_LIMIT_MAX:
        # a slot frees up when the (len-MAX+1)-th oldest request leaves the window
        frees_at = stamps[len(stamps) - config.RATE_LIMIT_MAX] + window
        retry_after = max(1, math.ceil((frees_at - now).total_seconds()))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    row = ApiUsage(api_key_hash=owner, session_id=session_id)
    db.add(row)
    db.commit()
    return row
