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
