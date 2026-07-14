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

    created = client.post("/api/sessions", json={"title": "æµ‹è¯•ä¼šè¯"}, headers=headers)
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]

    append_message("user_1001", session_id, "user", "å¸®æˆ‘æŸ¥ä¸€ä¸‹è®¢å•")
    append_message("user_1001", session_id, "assistant", "è®¢å•è®°å½•å·²æ‰¾åˆ°")

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
        yield 'data: {"type":"status","status":"thinking","message":"æ­£åœ¨æ€è€ƒ"}\n\n'
        append_message(user_id, session_id, "assistant", "è¿™æ˜¯æµ‹è¯•å›žç­”")
        yield 'data: {"type":"content","content":"è¿™æ˜¯æµ‹è¯•å›žç­”"}\n\n'
        yield 'data: {"type":"done","done":true}\n\n'

    monkeypatch.setattr(chat_router, "stream_chat", fake_stream_chat)

    payload = login(client)
    headers = auth_headers(payload)
    created = client.post("/api/sessions", json={"title": "chat"}, headers=headers)
    session_id = created.json()["session_id"]

    response = client.post("/api/chat", json={"query": "æµ‹è¯• SSE", "session_id": session_id}, headers=headers)
    assert response.status_code == 200, response.text
    events = parse_sse(response.text)
    assert [event["type"] for event in events] == ["status", "content", "done"]

    messages = client.get(f"/api/sessions/{session_id}/messages", headers=headers).json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "è¿™æ˜¯æµ‹è¯•å›žç­”"

def test_stream_chat_writes_agent_trace(monkeypatch, client):
    import asyncio
    from service import chat_service
    from infra.db import get_db_connection

    class Message:
        content = "Trace answer"

    class FakeGraph:
        async def ainvoke(self, state, config=None):
            return {"messages": [Message()], "next_agent": "product_agent", "metadata": {}}

    async def no_cache(query, user_id):
        return None

    async def collect_stream(query, user_id, session_id):
        chunks = []
        async for chunk in chat_service.stream_chat(query, user_id, session_id):
            chunks.append(chunk)
        return chunks

    monkeypatch.setattr(chat_service.semantic_cache, "get_cache", no_cache)
    monkeypatch.setattr(chat_service, "graph", FakeGraph())
    monkeypatch.setattr(chat_service, "memory", None)

    payload = login(client)
    headers = auth_headers(payload)
    created = client.post("/api/sessions", json={"title": "trace"}, headers=headers)
    session_id = created.json()["session_id"]

    chunks = asyncio.run(collect_stream("trace this request", "user_1001", session_id))
    events = parse_sse("".join(chunks))
    assert events[-1]["type"] == "done"

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, route_agent, duration_ms, error_message, JSON_LENGTH(stages) AS stage_count
                FROM agent_call_traces
                WHERE session_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            )
            trace = cursor.fetchone()

    assert trace["status"] == "success"
    assert trace["route_agent"] == "product_agent"
    assert trace["duration_ms"] is not None
    assert trace["error_message"] is None
    assert trace["stage_count"] >= 4

def test_demo_mode_stream_chat_is_offline_and_persists_trace(monkeypatch, client):
    import asyncio
    from service import chat_service
    from infra.db import get_db_connection

    async def fail_if_cache_called(query, user_id):
        raise AssertionError("semantic cache should not be called in demo mode")

    class FailGraph:
        async def ainvoke(self, state, config=None):
            raise AssertionError("real agent graph should not be called in demo mode")

    async def collect_stream(query, user_id, session_id):
        chunks = []
        async for chunk in chat_service.stream_chat(query, user_id, session_id):
            chunks.append(chunk)
        return chunks

    monkeypatch.setattr(chat_service.app_settings, "agent_demo_mode", True)
    monkeypatch.setattr(chat_service.semantic_cache, "get_cache", fail_if_cache_called)
    monkeypatch.setattr(chat_service, "graph", FailGraph())
    monkeypatch.setattr(chat_service, "memory", None)

    payload = login(client)
    headers = auth_headers(payload)
    created = client.post("/api/sessions", json={"title": "demo"}, headers=headers)
    session_id = created.json()["session_id"]

    chunks = asyncio.run(collect_stream("帮我查一下最近的订单记录", "user_1001", session_id))
    events = parse_sse("".join(chunks))

    assert [event["type"] for event in events if event["type"] != "content"] == [
        "status",
        "status",
        "status",
        "status",
        "done",
    ]
    assert "订单" in "".join(event.get("content", "") for event in events)

    messages = client.get(f"/api/sessions/{session_id}/messages", headers=headers).json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert "订单" in messages[1]["content"]

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, route_agent, error_message, JSON_LENGTH(stages) AS stage_count
                FROM agent_call_traces
                WHERE session_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            )
            trace = cursor.fetchone()

    assert trace["status"] == "success"
    assert trace["route_agent"] == "order_agent"
    assert trace["error_message"] is None
    assert trace["stage_count"] >= 4


def test_trace_api_requires_auth_and_is_user_scoped(client):
    from service.agent_trace_service import append_trace_stage, finish_trace, start_trace

    assert client.get("/api/traces/recent").status_code == 401

    user1 = login(client, "user_1001")
    user2 = login(client, "user_1002")
    headers1 = auth_headers(user1)
    headers2 = auth_headers(user2)

    created = client.post("/api/sessions", json={"title": "trace api"}, headers=headers1)
    session_id = created.json()["session_id"]
    trace_id = start_trace("user_1001", session_id, "查询账单")
    append_trace_stage(trace_id, "thinking", "正在理解问题...")
    append_trace_stage(trace_id, "agent_routing", "已路由到账单 Agent")
    finish_trace(trace_id, status="success", route_agent="billing_agent", duration_ms=123)

    session_traces = client.get(f"/api/sessions/{session_id}/traces", headers=headers1)
    assert session_traces.status_code == 200, session_traces.text
    trace = session_traces.json()[0]
    assert trace["route_agent"] == "billing_agent"
    assert trace["duration_ms"] == 123
    assert trace["stages"][0]["status"] == "thinking"

    recent = client.get("/api/traces/recent?limit=5", headers=headers1)
    assert recent.status_code == 200
    assert recent.json()[0]["trace_id"] == trace_id

    assert client.get(f"/api/sessions/{session_id}/traces", headers=headers2).status_code == 404
    assert client.get("/api/traces/recent?limit=5", headers=headers2).json() == []
