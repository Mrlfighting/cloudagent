import json

from service.session_service import append_message


def login(client, username="user_1001", password="Cloud@123456"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token_payload):
    return {"Authorization": f"Bearer {token_payload['access_token']}"}


def parse_sse(text):
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_login_refresh_logout_flow(client):
    payload = login(client)
    assert payload["token_type"] == "bearer"
    assert payload["user"]["user_id"] == "user_1001"

    bad_login = client.post("/api/auth/login", json={"username": "user_1001", "password": "bad"})
    assert bad_login.status_code == 401

    refresh = client.post("/api/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert refresh.status_code == 200, refresh.text
    refreshed = refresh.json()
    assert refreshed["refresh_token"] != payload["refresh_token"]

    logout = client.post(
        "/api/auth/logout",
        json={"refresh_token": refreshed["refresh_token"]},
        headers=auth_headers(refreshed),
    )
    assert logout.status_code == 200

    refresh_after_logout = client.post("/api/auth/refresh", json={"refresh_token": refreshed["refresh_token"]})
    assert refresh_after_logout.status_code == 401


def test_sessions_require_authentication(client):
    assert client.get("/api/sessions").status_code == 401
    assert client.post("/api/chat", json={"query": "hello", "session_id": "missing"}).status_code == 401


def test_session_lifecycle_and_soft_delete(client):
    payload = login(client)
    headers = auth_headers(payload)

    created = client.post("/api/sessions", json={"title": "测试会话"}, headers=headers)
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]

    append_message("user_1001", session_id, "user", "帮我查一下订单")
    append_message("user_1001", session_id, "assistant", "订单记录已找到")

    messages = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert messages.status_code == 200
    assert [item["role"] for item in messages.json()] == ["user", "assistant"]

    sessions = client.get("/api/sessions", headers=headers)
    assert sessions.status_code == 200
    assert sessions.json()[0]["message_count"] == 2

    deleted = client.delete(f"/api/sessions/{session_id}", headers=headers)
    assert deleted.status_code == 204

    sessions_after_delete = client.get("/api/sessions", headers=headers)
    assert sessions_after_delete.status_code == 200
    assert sessions_after_delete.json() == []

    hidden_messages = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert hidden_messages.status_code == 404


def test_cross_user_session_isolation(client):
    user1 = login(client, "user_1001")
    user2 = login(client, "user_1002")
    created = client.post("/api/sessions", json={"title": "user1 only"}, headers=auth_headers(user1))
    session_id = created.json()["session_id"]

    assert client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers(user2)).status_code == 404
    assert client.delete(f"/api/sessions/{session_id}", headers=auth_headers(user2)).status_code == 404


def test_chat_sse_persists_messages(monkeypatch, client):
    from router import chat as chat_router

    async def fake_stream_chat(query, user_id, session_id):
        append_message(user_id, session_id, "user", query)
        yield 'data: {"type":"status","status":"thinking","message":"正在思考"}\n\n'
        append_message(user_id, session_id, "assistant", "这是测试回答")
        yield 'data: {"type":"content","content":"这是测试回答"}\n\n'
        yield 'data: {"type":"done","done":true}\n\n'

    monkeypatch.setattr(chat_router, "stream_chat", fake_stream_chat)

    payload = login(client)
    headers = auth_headers(payload)
    created = client.post("/api/sessions", json={"title": "chat"}, headers=headers)
    session_id = created.json()["session_id"]

    response = client.post("/api/chat", json={"query": "测试 SSE", "session_id": session_id}, headers=headers)
    assert response.status_code == 200, response.text
    events = parse_sse(response.text)
    assert [event["type"] for event in events] == ["status", "content", "done"]

    messages = client.get(f"/api/sessions/{session_id}/messages", headers=headers).json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "这是测试回答"
