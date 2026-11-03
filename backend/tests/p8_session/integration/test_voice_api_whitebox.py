"""Voice wiring with a real instance on disk."""

import json
import sqlite3

from fastapi.testclient import TestClient

from digital_me.config import create
from digital_me.server import build_context, create_app
from digital_me.server.app import _warm_up_speech
from digital_me.tts import KokoroEngine, LanguageRouter, MmsEngine, SyspinEngine


def test_english_only_instance_uses_kokoro_alone(instances_home):
    instance = create("bob")
    instance.settings_path.write_text("listening:\n  languages: [en]\n", encoding="utf-8")
    engine = build_context(instance).speech.engine
    assert engine.languages == ["en"] and isinstance(engine._engines["en"], KokoroEngine)


def test_male_instance_uses_male_voices(instances_home):
    instance = create("ravi")
    instance.settings_path.write_text("voice:\n  gender: male\n", encoding="utf-8")
    engine = build_context(instance).speech.engine
    assert isinstance(engine._engines["te"], MmsEngine)
    assert {v.gender for v in engine.voices()} == {"male"}


def test_build_context_uses_kokoro_and_settings_defaults(instances_home):
    instance = create("alice")
    instance.settings_path.write_text("voice:\n  voice: bm_george\n  speed: 1.2\n", encoding="utf-8")
    context = build_context(instance)
    engine = context.speech.engine
    assert isinstance(engine, LanguageRouter) and engine.languages == ["en", "te"]
    assert isinstance(engine._engines["en"], KokoroEngine)
    assert isinstance(engine._engines["te"], SyspinEngine)  # female by default
    assert {v.gender for v in engine.voices()} == {"female"}
    current = context.speech.preferences.get()
    assert (current.voice, current.speed) == ("bm_george", 1.2)


def test_ui_change_persisted_in_instance_database(instances_home, fake_tts_factory, fake_llm_factory):
    instance = create("alice")
    context = build_context(instance, llm=fake_llm_factory(), tts=fake_tts_factory())
    client = TestClient(create_app(context, frontend_dist=None), base_url="http://localhost")
    client.put("/api/voice", json={"enabled": False})
    context.database.close()
    raw = sqlite3.connect(instance.database_path)
    value = raw.execute("SELECT value FROM preferences WHERE key='voice'").fetchone()[0]
    raw.close()
    assert json.loads(value)["enabled"] is False


async def test_warm_up_status_transitions(make_context, make_speech, fake_tts_factory):
    context = make_context()
    context.speech = make_speech()
    await _warm_up_speech(context)
    assert context.speech_status == "ready" and context.speech.engine.warmed


async def test_warm_up_failure_reported_not_raised(make_context, make_speech, fake_tts_factory):
    class Broken(fake_tts_factory):
        def warm_up(self, voice="v1"):
            raise RuntimeError("no model")

    context = make_context()
    context.speech = make_speech(Broken())
    await _warm_up_speech(context)
    assert context.speech_status == "error: no model"


async def test_warm_up_without_speech_is_noop(make_context):
    context = make_context()
    await _warm_up_speech(context)
    assert context.speech_status == "off"
