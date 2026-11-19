import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_owner
from app.crud import get_owned_session
from app.database import get_db
from app.models import ChatSession, Message
from app.schemas import MessageOut, SessionCreate, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(get_owner)])


@router.post("", response_model=SessionOut, status_code=201)
def create_session(
    body: SessionCreate | None = None,
    owner: str = Depends(get_owner),
    db: Session = Depends(get_db),
):
    s = ChatSession(api_key_hash=owner, title=body.title if body else None)
    db.add(s)
    db.commit()
    return s


@router.get("", response_model=list[SessionOut])
def list_sessions(owner: str = Depends(get_owner), db: Session = Depends(get_db)):
    return db.scalars(
        select(ChatSession)
        .where(ChatSession.api_key_hash == owner)
        .order_by(ChatSession.created_at.desc())
    ).all()


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: uuid.UUID, owner: str = Depends(get_owner), db: Session = Depends(get_db)):
    """Per-session token + cost totals."""
    return get_owned_session(db, session_id, owner)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: uuid.UUID, owner: str = Depends(get_owner), db: Session = Depends(get_db)):
    get_owned_session(db, session_id, owner)
    return db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.id)
    ).all()


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: uuid.UUID, owner: str = Depends(get_owner), db: Session = Depends(get_db)):
    s = get_owned_session(db, session_id, owner)
    db.delete(s)  # messages go with it (ORM cascade + ON DELETE CASCADE)
    db.commit()
    return Response(status_code=204)
