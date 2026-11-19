from tests.conftest import A, B


def new_session(client, headers=A):
    r = client.post("/sessions", json={"title": "t"}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_requires_api_key(client):
    assert client.post("/sessions").status_code == 401
    assert client.post("/sessions", headers={"X-API-Key": "nope"}).status_code == 401
    assert client.get("/usage").status_code == 401


def test_session_crud(client):
    sid = new_session(client)
    assert client.get(f"/sessions/{sid}/messages", headers=A).json() == []
    assert client.delete(f"/sessions/{sid}", headers=A).status_code == 204
    assert client.get(f"/sessions/{sid}/messages", headers=A).status_code == 404


def test_chat_streams_and_persists(client):
    sid = new_session(client)
    r = client.post(f"/sessions/{sid}/chat", json={"message": "hello"}, headers=A)
    assert r.status_code == 200 and r.text == "saw:hello"
    msgs = client.get(f"/sessions/{sid}/messages", headers=A).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["content"] == "saw:hello" and msgs[1]["tokens"] == 5
    s = client.get(f"/sessions/{sid}", headers=A).json()
    assert s["prompt_tokens"] == 10 and s["completion_tokens"] == 5 and s["cost_usd"] > 0


def test_history_is_sent_to_the_llm(client):
    sid = new_session(client)
    client.post(f"/sessions/{sid}/chat", json={"message": "one"}, headers=A)
    r = client.post(f"/sessions/{sid}/chat", json={"message": "two"}, headers=A)
    assert r.text == "saw:one|saw:one|two"


def test_sessions_are_isolated(client):
    s1, s2 = new_session(client), new_session(client)
    client.post(f"/sessions/{s1}/chat", json={"message": "secret"}, headers=A)
    r = client.post(f"/sessions/{s2}/chat", json={"message": "other"}, headers=A)
    assert "secret" not in r.text
    # another API key cannot see or use the session
    assert client.get(f"/sessions/{s1}/messages", headers=B).status_code == 404
    assert client.post(f"/sessions/{s1}/chat", json={"message": "x"}, headers=B).status_code == 404


def test_rate_limit_21st_message(client):
    sid = new_session(client)
    for i in range(20):
        assert client.post(f"/sessions/{sid}/chat", json={"message": f"m{i}"}, headers=A).status_code == 200
    r = client.post(f"/sessions/{sid}/chat", json={"message": "one too many"}, headers=A)
    assert r.status_code == 429
    assert r.json() == {"detail": "Rate limit exceeded"}
    assert int(r.headers["Retry-After"]) > 0
    # per key: key B is unaffected, and deleting the session doesn't reset the quota
    sid_b = new_session(client, B)
    assert client.post(f"/sessions/{sid_b}/chat", json={"message": "hi"}, headers=B).status_code == 200
    client.delete(f"/sessions/{sid}", headers=A)
    sid2 = new_session(client)
    assert client.post(f"/sessions/{sid2}/chat", json={"message": "hi"}, headers=A).status_code == 429


def test_usage_endpoint(client):
    sid = new_session(client)
    client.post(f"/sessions/{sid}/chat", json={"message": "hi"}, headers=A)
    u = client.get("/usage", headers=A).json()
    assert u["total_requests"] == 1 and u["total_tokens"] == 15
    assert u["rate_limit"]["remaining"] == 19
