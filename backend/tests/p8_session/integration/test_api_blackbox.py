"""Spec, driven only through HTTP and the WebSocket like the browser does."""

import pytest
from starlette.websockets import WebSocketDisconnect


def receive_until(ws, kind, limit=50):
    events = []
    for _ in range(limit):
        event = ws.receive_json()
        events.append(event)
        if event["type"] == kind:
            return events
    raise AssertionError(f"no {kind} event in {events}")


def test_status_reports_persona_and_disclosure(make_client):
    body = make_client().get("/api/status").json()
    assert body["persona_name"] == "Sam"
    assert body["instance"] == "test"
    assert "AI-generated" in body["disclosure"]
    assert body["llm"]["reachable"] is True


def test_full_conversation_over_websocket(make_client, origin_header, fake_llm_factory):
    client = make_client(fake_llm_factory(["[happy] Hi Sam here. ", "How can I help?"]))
    with client.websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "conversation"
        assert ws.receive_json() == {"type": "state", "state": "idle"}
        ws.send_json({"type": "user_message", "text": "Hello"})
        events = receive_until(ws, "assistant_done")
        assert events[-1]["message"]["content"] == "Hi Sam here. How can I help?"
        assert [e["text"] for e in events if e["type"] == "sentence"] == ["Hi Sam here.", "How can I help?"]
        conversation_id = hello["conversation_id"]

    history = client.get(f"/api/conversations/{conversation_id}").json()
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]
    listing = client.get("/api/conversations").json()
    assert listing[0]["title"] == "Hello" and listing[0]["message_count"] == 2


def test_reconnect_resumes_latest_conversation(make_client, origin_header):
    client = make_client()
    with client.websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "remember me"})
        receive_until(ws, "assistant_done")
    with client.websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        hello = ws.receive_json()
        assert hello["messages"][0]["content"] == "remember me"


def test_delete_conversation(make_client, store):
    conv = store.create_conversation()
    client = make_client()
    assert client.delete(f"/api/conversations/{conv}").status_code == 204
    assert client.delete(f"/api/conversations/{conv}").status_code == 404
    assert client.get(f"/api/conversations/{conv}").status_code == 404


def test_foreign_host_header_rejected(make_client):
    response = make_client().get("/api/status", headers={"host": "evil.example"})
    assert response.status_code == 400


def test_foreign_origin_websocket_rejected(make_client):
    with pytest.raises(WebSocketDisconnect) as info:
        with make_client().websocket_connect("ws://localhost/ws", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_json()
    assert info.value.code == 1008


def test_bad_json_frame_closes_socket(make_client, origin_header):
    with make_client().websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_text("not json")
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 1003


def test_api_docs_disabled(make_client):
    client = make_client()
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
