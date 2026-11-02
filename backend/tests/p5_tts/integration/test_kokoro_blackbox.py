"""Real Kokoro model: spoken output has plausible length, ordered word timings and honours speed."""

import pytest

pytestmark = pytest.mark.live

SENTENCE = "Hi, I'm Alex. I really enjoy rock climbing on the weekends."


def test_produces_speech_with_word_timings(real_kokoro):
    synthesis = real_kokoro.synthesize(SENTENCE, "af_heart", 1.0)
    assert 2.0 < synthesis.duration < 8.0
    spoken = [w.text.lower() for w in synthesis.words]
    assert "climbing" in spoken and "weekends" in spoken
    starts = [w.start for w in synthesis.words]
    assert starts == sorted(starts)
    assert all(0 <= w.start <= w.end <= synthesis.duration + 0.05 for w in synthesis.words)


def test_faster_speed_is_shorter(real_kokoro):
    normal = real_kokoro.synthesize(SENTENCE, "am_michael", 1.0).duration
    fast = real_kokoro.synthesize(SENTENCE, "am_michael", 1.5).duration
    assert fast < normal * 0.85


@pytest.mark.parametrize("voice", ["af_heart", "am_fenrir", "bf_emma", "bm_george"])
def test_every_accent_and_gender_speaks(real_kokoro, voice):
    assert real_kokoro.synthesize("Good morning.", voice, 1.0).duration > 0.3
