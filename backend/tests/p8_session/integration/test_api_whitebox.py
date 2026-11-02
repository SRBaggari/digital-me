"""Full app with real SQLite on disk; asserts on internal effects (rows, flags, wiring)."""

import sqlite3
import time

from fastapi.testclient import TestClient

from digital_me.config import create
from digital_me.server import build_context, create_app


def drain_until(ws, kind):
    while (event := ws.receive_json())["type"] != kind:
        pass
    return event


def test_build_context_wires_instance_files(instances_home, fake_llm_factory):
    instance = create("alice")
    instance.profile_path.write_text("name: Alice\ninterests: [rowing]\n", encoding="utf-8")
    context = build_context(instance, llm=fake_llm_factory())
    assert context.instance_name == "alice"
    assert "rowing" in context.engine.system_prompt
    assert context.database.path == instance.database_path


def test_build_context_defaults_to_local_ollama(instances_home):
    context = build_context(create("alice"))
    assert context.llm.base_url == "http://127.0.0.1:11434"


def test_interrupted_turn_flag_written_to_disk(instances_home, fake_llm_factory):
    instance = create("alice")
    llm = fake_llm_factory(["[neutral] one ", "two ", "three ", "four."], delay=0.1)
    context = build_context(instance, llm=llm)
    client = TestClient(create_app(context, frontend_dist=None), base_url="http://localhost")
    with client.websocket_connect("ws://localhost/ws", headers={"origin": "http://localhost:8765"}) as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "go"})
        drain_until(ws, "assistant_delta")
        ws.send_json({"type": "interrupt"})
        drain_until(ws, "assistant_interrupted")
    context.database.close()
    raw = sqlite3.connect(instance.database_path)
    rows = raw.execute("SELECT role, interrupted FROM messages ORDER BY id").fetchall()
    raw.close()
    assert rows == [("user", 0), ("assistant", 1)]


def test_frontend_served_when_built(tmp_path, make_context):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>Digital Me</h1>", encoding="utf-8")
    client = TestClient(create_app(make_context(), frontend_dist=dist), base_url="http://localhost")
    assert "Digital Me" in client.get("/").text
    assert client.get("/api/status").status_code == 200


def test_disconnect_mid_turn_cancels_task(make_context, fake_llm_factory, store):
    context = make_context(fake_llm_factory(["[neutral] a ", "b ", "c."], delay=0.1))
    client = TestClient(create_app(context, frontend_dist=None), base_url="http://localhost")
    with client.websocket_connect("ws://localhost/ws", headers={"origin": "http://localhost:8765"}) as ws:
        hello = ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "hi"})
        drain_until(ws, "assistant_delta")
    time.sleep(0.4)
    messages = store.get_messages(hello["conversation_id"])
    assert messages[-1].role == "assistant" and messages[-1].interrupted
