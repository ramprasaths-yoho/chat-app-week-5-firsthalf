import os

# must be set before the app is imported
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["API_KEYS"] = "key-a,key-b"
os.environ["OPENAI_API_KEY"] = "test"

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.database import Base, engine
from app.main import app
from app.routes import chat as chat_route

A = {"X-API-Key": "key-a"}
B = {"X-API-Key": "key-b"}


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    def fake_stream(messages, usage: llm.Usage):
        # echo what the "model" saw so history/isolation is testable
        seen = [m["content"] for m in messages if m["role"] != "system"]
        usage.prompt_tokens, usage.completion_tokens = 10, 5
        yield "saw:"
        yield "|".join(seen)

    monkeypatch.setattr(chat_route, "stream_chat", fake_stream)


@pytest.fixture
def client():
    return TestClient(app)
