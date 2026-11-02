"""Spec: the voice can be listed, changed, previewed and switched off through the API,
and spoken replies arrive over the WebSocket."""

import io
import wave


def test_get_voice(make_client, make_speech):
    body = make_client(speech=make_speech()).get("/api/voice").json()
    assert body["settings"] == {"enabled": True, "voice": "v1", "speed": 1.0}
    assert [v["id"] for v in body["voices"]] == ["v1", "v2"]
    assert body["engine"] == "fake"


def test_change_voice_and_speed(make_client, make_speech):
    client = make_client(speech=make_speech())
    body = client.put("/api/voice", json={"voice": "v2", "speed": 1.25}).json()
    assert body["settings"] == {"enabled": True, "voice": "v2", "speed": 1.25}
    assert client.get("/api/voice").json()["settings"]["voice"] == "v2"


def test_unknown_voice_rejected(make_client, make_speech):
    response = make_client(speech=make_speech()).put("/api/voice", json={"voice": "nope"})
    assert response.status_code == 422


def test_invalid_speed_rejected(make_client, make_speech):
    assert make_client(speech=make_speech()).put("/api/voice", json={"speed": 5}).status_code == 422


def test_preview_returns_playable_wav(make_client, make_speech):
    response = make_client(speech=make_speech()).post("/api/voice/preview", json={"voice": "v2"})
    assert response.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(response.content)) as wav:
        assert wav.getnframes() > 0


def test_preview_errors(make_client, make_speech, fake_tts_factory):
    client = make_client(speech=make_speech(fake_tts_factory(fail_on="sound")))
    assert client.post("/api/voice/preview", json={}).status_code == 503
    assert client.post("/api/voice/preview", json={"voice": "zz"}).status_code == 422
    assert client.post("/api/voice/preview", json={"text": ""}).status_code == 422


def test_voice_endpoints_absent_without_speech(make_client):
    assert make_client().get("/api/voice").status_code == 404


def test_spoken_reply_over_websocket(make_client, make_speech, origin_header, fake_llm_factory):
    client = make_client(fake_llm_factory(["[happy] Hi! ", "Bye."]), make_speech())
    with client.websocket_connect("ws://localhost/ws", headers=origin_header) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "hello"})
        events = []
        while (event := ws.receive_json()) != {"type": "state", "state": "idle"}:
            events.append(event)
    assert [e["text"] for e in events if e["type"] == "audio"] == ["Hi!", "Bye."]
    assert events[-1] == {"type": "speech_end"}


def test_status_reports_speech_ready_after_warm_up(make_client, make_speech):
    with make_client(speech=make_speech()) as client:  # `with` runs startup (warm-up)
        assert client.get("/api/status").json()["speech"] == "ready"
