from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.auth import get_owner
from app.database import get_db
from app.models import ApiUsage, utcnow

router = APIRouter(tags=["usage"], dependencies=[Depends(get_owner)])


@router.get("/usage")
def usage(owner: str = Depends(get_owner), db: Session = Depends(get_db)):
    """Bonus: usage totals for the calling API key."""
    total = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(ApiUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ApiUsage.completion_tokens), 0),
            func.coalesce(func.sum(ApiUsage.cost_usd), 0.0),
        ).where(ApiUsage.api_key_hash == owner)
    ).one()
    since = utcnow() - timedelta(seconds=config.RATE_LIMIT_WINDOW_SECONDS)
    last_hour = db.scalar(
        select(func.count()).where(ApiUsage.api_key_hash == owner, ApiUsage.created_at >= since)
    )
    return {
        "total_requests": total[0],
        "prompt_tokens": int(total[1]),
        "completion_tokens": int(total[2]),
        "total_tokens": int(total[1]) + int(total[2]),
        "cost_usd": round(float(total[3]), 6),
        "rate_limit": {
            "limit": config.RATE_LIMIT_MAX,
            "used_last_window": last_hour,
            "remaining": max(0, config.RATE_LIMIT_MAX - last_hour),
        },
    }
