"""Spec: through the real WebSocket, binary microphone audio becomes a spoken turn;
listening settings can be read and changed over HTTP."""

from starlette.websockets import WebSocketDisconnect


def receive_until(ws, predicate, limit=200):
    events = []
    for _ in range(limit):
        event = ws.receive_json()
        events.append(event)
        if predicate(event):
            return events
    raise AssertionError(events)


def test_talking_over_the_websocket(make_client, make_hearing, fake_transcriber_factory, origin_header, fake_llm_factory, speech_audio):
    client = make_client(fake_llm_factory(["[happy] Sure!"]), hearing=make_hearing(fake_transcriber_factory(["Can you hear me?"])))
    with client.websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "mic_start"})
        assert ws.receive_json() == {"type": "mic", "on": True}
        for _ in range(25):  # 25 x 40 ms of speech, then silence, in browser-sized frames
            ws.send_bytes(speech_audio.voice(40))
        for _ in range(25):
            ws.send_bytes(speech_audio.silence(40))
        events = receive_until(ws, lambda e: e.get("type") == "assistant_done")
    kinds = [e["type"] for e in events]
    assert kinds.index("user_speaking") < kinds.index("transcript") < kinds.index("user_message")
    assert next(e for e in events if e["type"] == "transcript")["text"] == "Can you hear me?"
    assert events[-1]["message"]["content"] == "Sure!"


def test_get_and_change_listening_settings(make_client, make_hearing):
    client = make_client(hearing=make_hearing())
    body = client.get("/api/listening").json()
    assert body["settings"] == {"enabled": True, "barge_in": True, "telugu_model": "base"}
    assert body["model"] == "base.en"
    changed = client.put("/api/listening", json={"barge_in": False}).json()
    assert changed["settings"]["barge_in"] is False


def test_invalid_listening_change_rejected(make_client, make_hearing):
    client = make_client(hearing=make_hearing())
    assert client.put("/api/listening", json={"model": "tiny.en"}).status_code == 422


def test_listening_api_absent_without_recognition(make_client):
    assert make_client().get("/api/listening").status_code == 404


def test_binary_audio_without_mic_is_harmless(make_client, make_hearing, origin_header, speech_audio):
    with make_client(hearing=make_hearing()).websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(speech_audio.voice(1000))
        ws.send_json({"type": "new_conversation"})
        assert ws.receive_json()["type"] == "conversation"


def test_text_frame_with_bad_json_still_closes(make_client, origin_header):
    import pytest

    with make_client().websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_text("{oops")
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 1003
