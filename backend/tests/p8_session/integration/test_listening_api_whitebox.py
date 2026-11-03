"""Listening wiring with a real instance on disk."""

from fastapi.testclient import TestClient

from digital_me.config import create
from digital_me.server import build_context, create_app
from digital_me.server.app import _warm_up, _warm_up_hearing
from digital_me.stt import BilingualTranscriber, SileroVAD, WhisperTranscriber


def test_build_context_english_only_uses_one_whisper_model(instances_home):
    instance = create("alice")
    instance.settings_path.write_text(
        "listening:\n  model: small.en\n  barge_in: false\n  languages: [en]\n", encoding="utf-8"
    )
    context = build_context(instance)
    assert isinstance(context.hearing.transcriber, WhisperTranscriber)
    assert context.hearing.transcriber.model_name == "small.en"
    assert context.hearing.vad_factory is SileroVAD
    assert context.hearing.preferences.get().barge_in is False


def test_build_context_bilingual_by_default(instances_home):
    context = build_context(create("alice"))
    transcriber = context.hearing.transcriber
    assert isinstance(transcriber, BilingualTranscriber)
    assert transcriber.languages == ["en", "te"]
    assert transcriber._transcribers["te"].language == "te"
    assert transcriber._transcribers["en"].model_name == "base.en"


async def test_warm_up_loads_recognition_after_voice(make_context, make_speech, make_hearing, fake_transcriber_factory):
    order = []
    transcriber = fake_transcriber_factory()
    transcriber.warm_up = lambda: order.append("hearing")
    context = make_context()
    context.speech = make_speech()
    original = context.speech.engine.warm_up
    context.speech.engine.warm_up = lambda voice: (order.append("speech"), original(voice))
    context.hearing = make_hearing(transcriber)
    await _warm_up(context)
    assert order == ["speech", "hearing"]
    assert context.hearing_status == "ready"


async def test_hearing_warm_up_failure_reported(make_context, make_hearing, fake_transcriber_factory):
    transcriber = fake_transcriber_factory()

    def fail():
        raise RuntimeError("no whisper")

    transcriber.warm_up = fail
    context = make_context()
    context.hearing = make_hearing(transcriber)
    await _warm_up_hearing(context)
    assert context.hearing_status == "error: no whisper"


async def test_switching_to_the_accurate_telugu_model_swaps_it_in_the_background(make_context, database, fake_transcriber_factory, monkeypatch):
    import asyncio

    from digital_me.config import ListeningSettings
    from digital_me.server import app as app_module
    from digital_me.server.listener import Hearing
    from digital_me.stt import BilingualTranscriber, ListeningPreferences

    old_te, new_te = fake_transcriber_factory(["old"]), fake_transcriber_factory(["new"])
    bilingual = BilingualTranscriber({"en": fake_transcriber_factory(), "te": old_te}, detector_factory=lambda: None)
    monkeypatch.setattr(app_module, "telugu_transcriber", lambda size: new_te)
    context = make_context()
    context.hearing = Hearing(bilingual, lambda: (lambda f: 0.0), ListeningPreferences(database, ListeningSettings()))
    await app_module._swap_telugu_model(context, "small")
    assert context.hearing_status == "loading"
    await asyncio.gather(*context.background_tasks)
    assert bilingual.transcriber_for("te") is new_te and new_te.warmed
    assert context.hearing_status == "ready"


def test_accurate_telugu_choice_is_remembered_across_restarts(instances_home, fake_llm_factory, fake_tts_factory, monkeypatch):
    from digital_me.server import app as app_module

    async def no_swap(context, size):  # loading the real model is not what this test is about
        pass

    monkeypatch.setattr(app_module, "_swap_telugu_model", no_swap)
    instance = create("alice")
    context = build_context(instance, llm=fake_llm_factory(), tts=fake_tts_factory())
    TestClient(create_app(context, frontend_dist=None), base_url="http://localhost").put(
        "/api/listening", json={"telugu_model": "small"}
    )
    context.database.close()
    restarted = build_context(instance, llm=fake_llm_factory(), tts=fake_tts_factory())
    assert restarted.hearing.transcriber.transcriber_for("te").model_name == "telugu-small"


def test_status_reports_hearing(make_client, make_hearing):
    with make_client(hearing=make_hearing()) as client:
        assert client.get("/api/status").json()["hearing"] == "ready"


def test_listening_change_persisted_in_instance_database(instances_home, fake_llm_factory, fake_tts_factory, make_hearing):
    instance = create("alice")
    context = build_context(instance, llm=fake_llm_factory(), tts=fake_tts_factory())
    client = TestClient(create_app(context, frontend_dist=None), base_url="http://localhost")
    client.put("/api/listening", json={"enabled": False})
    rows = context.database.query("SELECT value FROM preferences WHERE key = 'listening'")
    assert '"enabled": false' in rows[0]["value"]
