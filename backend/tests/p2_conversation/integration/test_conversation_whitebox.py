"""Engine + real Ollama client parsing (over a mock HTTP transport) + real SQLite file."""

import json
import sqlite3

import httpx

from digital_me.config import LLMSettings
from digital_me.conversation import ConversationEngine, ConversationStore, SentenceReady
from digital_me.db import Database
from digital_me.llm import OllamaClient


def ollama_stream(*chunks):
    lines = [{"message": {"content": c}, "done": False} for c in chunks]
    lines.append({"message": {"content": ""}, "done": True})
    body = "\n".join(json.dumps(line) for line in lines)
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, text=body)

    client = OllamaClient("http://127.0.0.1:11434", "m", transport=httpx.MockTransport(handler))
    return client, requests


async def test_full_turn_persists_rows_to_disk(tmp_path, profile, collect):
    path = tmp_path / "db.sqlite3"
    database = Database(path, "sam")
    store = ConversationStore(database)
    llm, requests = ollama_stream("[hap", "py] Hello", " there. ", "[serious] Be careful.")
    engine = ConversationEngine(profile, store, llm, LLMSettings())
    conv = store.create_conversation()

    events = await collect(engine.respond(conv, "Hi"))
    database.close()

    assert [(e.text, e.emotion) for e in events if isinstance(e, SentenceReady)] == [
        ("Hello there.", "happy"),
        ("Be careful.", "serious"),
    ]
    raw = sqlite3.connect(path)
    rows = raw.execute("SELECT role, content, emotion, interrupted FROM messages ORDER BY id").fetchall()
    raw.close()
    assert rows == [("user", "Hi", None, 0), ("assistant", "Hello there. Be careful.", "happy", 0)]
    assert requests[0]["messages"][0]["role"] == "system"
    assert "Sam" in requests[0]["messages"][0]["content"]


async def test_history_survives_restart(tmp_path, profile, collect):
    path = tmp_path / "db.sqlite3"
    first = Database(path, "sam")
    store = ConversationStore(first)
    llm, _ = ollama_stream("[neutral] Noted.")
    conv = store.create_conversation()
    await collect(ConversationEngine(profile, store, llm, LLMSettings()).respond(conv, "I like tea."))
    first.close()

    second = Database(path, "sam")
    llm2, requests = ollama_stream("[neutral] Tea.")
    await collect(
        ConversationEngine(profile, ConversationStore(second), llm2, LLMSettings()).respond(conv, "What do I like?")
    )
    sent = [m["content"] for m in requests[0]["messages"]]
    assert sent[1:] == ["I like tea.", "[neutral] Noted.", "What do I like?"]
    second.close()
