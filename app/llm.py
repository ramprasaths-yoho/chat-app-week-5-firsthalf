import logging
from dataclasses import dataclass
from typing import Iterator

import openai
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app import config

log = logging.getLogger("chatapp.llm")

RETRYABLE = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)

_client = None


def get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            timeout=30,
        )
    return _client


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _should_retry(exc: BaseException) -> bool:
    # An empty account can't be fixed by retrying.
    if isinstance(exc, openai.RateLimitError) and getattr(exc, "code", None) == "insufficient_quota":
        return False
    return isinstance(exc, RETRYABLE)


def _log_retry(retry_state) -> None:
    log.warning("LLM call failed, retrying: %s", retry_state.outcome.exception())


@retry(
    retry=retry_if_exception(_should_retry),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
    before_sleep=_log_retry,
)
def _open_stream(messages):
    # Retrying is only safe BEFORE the first token has been sent to the client.
    kwargs = dict(model=config.LLM_MODEL, messages=messages, stream=True)
    if not config.OPENAI_BASE_URL:
        kwargs["stream_options"] = {"include_usage": True}
    return get_client().chat.completions.create(**kwargs)


def stream_chat(messages, usage: Usage) -> Iterator[str]:
    """Yield text deltas; fills `usage` from the final chunk when the provider sends it."""
    stream = _open_stream(messages)
    for chunk in stream:
        if getattr(chunk, "usage", None):
            usage.prompt_tokens = chunk.usage.prompt_tokens
            usage.completion_tokens = chunk.usage.completion_tokens
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
