"""Spec: a fixed catalogue of English voices; unknown voices are rejected; speed is passed on."""

import pytest

from digital_me.tts import TTSError


def test_voice_catalogue(make_kokoro):
    voices = make_kokoro().voices()
    ids = [v.id for v in voices]
    assert len(ids) == len(set(ids))
    assert {v.accent for v in voices} == {"American", "British"}
    assert {v.gender for v in voices} == {"female", "male"}
    assert "af_heart" in ids


@pytest.mark.parametrize("voice", ["", "xx_nobody", "AF_HEART", "../af_heart"])
def test_unknown_voice_rejected(make_kokoro, voice):
    with pytest.raises(TTSError):
        make_kokoro().synthesize("Hello", voice, 1.0)


def test_returns_audio_and_word_timings(make_kokoro):
    synthesis = make_kokoro().synthesize("Hi", "af_heart", 1.0)
    assert synthesis.sample_rate == 24_000
    assert synthesis.duration > 0
    assert synthesis.words[0].text == "Hi"


def test_speed_and_voice_forwarded(make_kokoro, pipelines):
    make_kokoro().synthesize("Hi", "am_puck", 1.4)
    assert pipelines["a"].calls == [("Hi", "am_puck", 1.4)]
