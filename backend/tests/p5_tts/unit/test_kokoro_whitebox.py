import pytest

from digital_me.tts import KokoroEngine, TTSError
from digital_me.tts import kokoro_engine as ke


def test_word_offsets_accumulate_across_chunks(make_kokoro, fake_token, fake_result):
    engine = make_kokoro(
        [
            fake_result(1.0, [fake_token("One", 0.1, 0.4)]),
            fake_result(0.5, [fake_token("two", 0.0, 0.2)]),
        ]
    )
    synthesis = engine.synthesize("One. two.", "af_heart", 1.0)
    assert [(w.text, w.start, w.end) for w in synthesis.words] == [("One", 0.1, 0.4), ("two", 1.0, 1.2)]
    assert synthesis.duration == pytest.approx(1.5)


def test_tokens_without_timestamps_or_text_are_skipped(make_kokoro, fake_token, fake_result):
    engine = make_kokoro([fake_result(1.0, [fake_token("a", None, 0.2), fake_token(" ", 0.1, 0.2), fake_token("b", 0.3, 0.5)])])
    assert [w.text for w in engine.synthesize("a b", "af_heart", 1.0).words] == ["b"]


def test_chunks_without_audio_are_skipped(make_kokoro, fake_result):
    from types import SimpleNamespace

    engine = make_kokoro([SimpleNamespace(audio=None, tokens=[]), fake_result(0.25, [])])
    assert engine.synthesize("x", "af_heart", 1.0).duration == pytest.approx(0.25)


def test_one_pipeline_per_accent_reused(make_kokoro, pipelines):
    engine = make_kokoro()
    engine.synthesize("a", "af_heart", 1.0)
    engine.synthesize("b", "am_michael", 1.0)
    engine.synthesize("c", "bf_emma", 1.0)
    assert sorted(pipelines) == ["a", "b"]
    assert len(pipelines["a"].calls) == 2


def test_library_errors_wrapped(make_kokoro):
    engine = make_kokoro(error=RuntimeError("cuda exploded"))
    with pytest.raises(TTSError, match="cuda exploded"):
        engine.synthesize("hi", "af_heart", 1.0)


def test_empty_text_skips_the_model(make_kokoro, pipelines):
    synthesis = make_kokoro().synthesize("   ", "af_heart", 1.0)
    assert synthesis.duration == 0 and pipelines == {}


def test_ready_after_first_load(make_kokoro):
    engine = make_kokoro()
    assert not engine.ready
    engine.warm_up()
    assert engine.ready


def test_fetch_uses_cache_without_network_when_present():
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return "/cache/config.json"

    assert ke.fetch("config.json", download) == "/cache/config.json"
    assert calls == [{"repo_id": ke.REPO_ID, "filename": "config.json", "local_files_only": True}]


def test_fetch_downloads_once_when_missing():
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        if kwargs.get("local_files_only"):
            raise FileNotFoundError("not cached")
        return "/cache/voices/af_heart.pt"

    assert ke.fetch("voices/af_heart.pt", download) == "/cache/voices/af_heart.pt"
    assert [c.get("local_files_only", False) for c in calls] == [True, False]


def test_voice_resolved_to_local_file_before_synthesis():
    seen = []

    def pipeline(text, voice, speed):
        seen.append(voice)
        return iter([])

    engine = KokoroEngine(pipeline_factory=lambda code: pipeline, voice_path=lambda v: f"/cache/voices/{v}.pt")
    engine.synthesize("Hi", "af_heart", 1.0)
    assert seen == ["/cache/voices/af_heart.pt"]


def test_lang_code_from_voice_prefix():
    assert ke.lang_code("af_heart") == "a"
    assert ke.lang_code("bm_george") == "b"
