import numpy as np
import pytest

from digital_me.stt import FRAME, SpeechDetector, SpeechEnded, SpeechStarted


def scripted(probs):
    """Detector whose per-frame probabilities come from a list."""
    it = iter(probs)
    return SpeechDetector(lambda frame: next(it))


def frames(n, value=0.0):
    return np.full(n * FRAME, value, dtype=np.float32)


def test_partial_frames_are_buffered_across_feeds():
    calls = []
    detector = SpeechDetector(lambda f: calls.append(len(f)) or 0.0)
    detector.feed(np.zeros(300, dtype=np.float32))
    assert calls == []
    detector.feed(np.zeros(300, dtype=np.float32))
    assert calls == [FRAME]
    assert len(detector._pending) == 600 - FRAME


def test_start_needs_min_speech_frames():
    detector = scripted([1.0] * 8)  # 8 x 32 ms = 256 ms >= 250 ms
    events = detector.feed(frames(8))
    assert events == [SpeechStarted()]
    assert detector.speaking


def test_short_blip_becomes_pre_roll_not_speech():
    detector = scripted([1.0] * 3 + [0.0] * 2)
    assert detector.feed(frames(5)) == []
    assert not detector.speaking
    assert len(detector._pre_roll) == 5


def test_pre_roll_is_capped():
    detector = scripted([0.0] * 50)
    detector.feed(frames(50))
    assert len(detector._pre_roll) == 300 // 32


def test_utterance_includes_pre_roll():
    detector = scripted([0.0] * 9 + [1.0] * 8 + [0.0] * 22)
    events = detector.feed(frames(9 + 8 + 22))
    ended = [e for e in events if isinstance(e, SpeechEnded)][0]
    pre_roll = 300 // 32
    assert len(ended.audio) == (pre_roll + 8 + 22) * FRAME


def test_hysteresis_keeps_speech_through_dips():
    # after starting at >= 0.5, values >= 0.35 still count as speech
    detector = scripted([1.0] * 8 + [0.4] * 40)
    events = detector.feed(frames(48))
    assert events == [SpeechStarted()]
    assert detector.speaking


def test_playback_raises_threshold_and_duration():
    detector = scripted([0.7] * 20)
    detector.playback = True
    assert detector.feed(frames(20)) == []  # 0.7 < 0.85
    loud = scripted([0.9] * 14 + [0.9])
    loud.playback = True
    assert loud.feed(frames(14)) == []  # 448 ms < 450 ms
    assert loud.feed(frames(1)) == [SpeechStarted()]


def test_max_utterance_forces_end_then_keeps_listening():
    detector = SpeechDetector(lambda f: 1.0, max_utterance_s=1.0)
    events = detector.feed(frames(48))
    assert [type(e) for e in events] == [SpeechStarted, SpeechEnded, SpeechStarted]
    assert events[1].duration == pytest.approx(1.0, abs=0.04)
    assert detector.speaking  # the still-continuing speech becomes the next utterance


def test_reset_clears_everything():
    detector = scripted([1.0] * 10)
    detector.feed(frames(10) [: 10 * FRAME - 5])
    detector.reset()
    assert not detector.speaking and len(detector._pending) == 0 and not detector._pre_roll
