import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import config
from app.auth import get_owner
from app.crud import get_owned_session
from app.database import SessionLocal, get_db
from app.llm import Usage, stream_chat
from app.memory import build_context, estimate_tokens
from app.models import ApiUsage, ChatSession, Message
from app.rate_limit import check_and_record
from app.schemas import ChatRequest

log = logging.getLogger("chatapp.chat")
router = APIRouter(prefix="/sessions", tags=["chat"], dependencies=[Depends(get_owner)])


def _persist(session_id: uuid.UUID, usage_id: int, answer: str, usage: Usage, context: list[dict]):
    """Runs after streaming ends. Uses its OWN DB session because the request-scoped
    one is already closed by the time a StreamingResponse generator finishes."""
    prompt_t = usage.prompt_tokens or sum(estimate_tokens(m["content"]) for m in context)
    completion_t = usage.completion_tokens or (estimate_tokens(answer) if answer else 0)
    cost = (prompt_t * config.PRICE_INPUT_PER_M + completion_t * config.PRICE_OUTPUT_PER_M) / 1_000_000

    with SessionLocal() as db:
        if answer:
            db.add(Message(session_id=session_id, role="assistant", content=answer, tokens=completion_t))
        db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(
                prompt_tokens=ChatSession.prompt_tokens + prompt_t,
                completion_tokens=ChatSession.completion_tokens + completion_t,
                cost_usd=ChatSession.cost_usd + cost,
            )
        )
        db.execute(
            update(ApiUsage)
            .where(ApiUsage.id == usage_id)
            .values(prompt_tokens=prompt_t, completion_tokens=completion_t, cost_usd=cost)
        )
        db.commit()


@router.post("/{session_id}/chat")
def chat(
    session_id: uuid.UUID,
    body: ChatRequest,
    owner: str = Depends(get_owner),
    db: Session = Depends(get_db),
):
    get_owned_session(db, session_id, owner)             # 401/404 first
    usage_row = check_and_record(db, owner, session_id)  # 429 if over the limit

    db.add(Message(session_id=session_id, role="user", content=body.message,
                   tokens=estimate_tokens(body.message)))
    db.commit()

    history = db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.id)
    ).all()                                              # full history from the DB...
    context = build_context(history)                     # ...then the sliding window
    usage_id = usage_row.id

    def event_stream():
        answer, usage = "", Usage()
        try:
            for piece in stream_chat(context, usage):
                answer += piece
                yield piece
        except Exception:  # tenacity gave up, or the stream broke mid-way
            log.exception("LLM call failed")
            yield config.FRIENDLY_ERROR
        finally:
            # also runs if the client disconnects, so partial answers are kept
            _persist(session_id, usage_id, answer, usage, context)

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")
