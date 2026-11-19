import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatSession


def get_owned_session(db: Session, session_id: uuid.UUID, owner: str) -> ChatSession:
    """Parameterised lookup scoped to the caller's key. Another key's session
    looks exactly like a missing one (404), which keeps sessions isolated."""
    s = db.scalar(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.api_key_hash == owner)
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s
