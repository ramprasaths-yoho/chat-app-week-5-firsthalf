"""Sliding-window memory: the FULL history is loaded from the DB on every call,
then trimmed to the newest messages that fit the budget."""
from app import config
from app.models import Message


def estimate_tokens(text: str) -> int:
    # ~4 chars per token heuristic; swap for tiktoken if you want exact counts
    return max(1, len(text) // 4)


def build_context(history: list[Message]) -> list[dict]:
    selected: list[Message] = []
    total = estimate_tokens(config.SYSTEM_PROMPT)

    for msg in reversed(history[-config.MAX_CONTEXT_MESSAGES:]):
        cost = msg.tokens or estimate_tokens(msg.content)
        # always keep the newest message, otherwise stop at the budget
        if selected and total + cost > config.MAX_CONTEXT_TOKENS:
            break
        selected.append(msg)
        total += cost

    selected.reverse()
    while len(selected) > 1 and selected[0].role != "user":  # don't start mid-answer
        selected.pop(0)

    return [{"role": "system", "content": config.SYSTEM_PROMPT}] + [
        {"role": m.role, "content": m.content} for m in selected
    ]
