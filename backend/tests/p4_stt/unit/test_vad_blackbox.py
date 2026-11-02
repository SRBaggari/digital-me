"""Spec: speech starts after >= 250 ms of speech and ends after >= 700 ms of silence;
anything shorter than 250 ms is ignored; while Digital Me is speaking, only clear, longer
speech counts."""

import numpy as np
import pytest

from digital_me.stt import SAMPLE_RATE, SpeechDetector, SpeechEnded, SpeechStarted


def loud_vad(frame):
    return 1.0 if float(np.abs(frame).mean()) > 0.1 else 0.0


def audio(*parts):
    """parts: (milliseconds, amplitude)"""
    return np.concatenate([np.full(SAMPLE_RATE * ms // 1000, amp, dtype=np.float32) for ms, amp in parts])


def run(stream, playback=False, chunk_ms=20):
    detector = SpeechDetector(loud_vad)
    detector.playback = playback
    step = SAMPLE_RATE * chunk_ms // 1000
    events = []
    for i in range(0, len(stream), step):
        events.extend(detector.feed(stream[i : i + step]))
    return events


def test_one_utterance():
    events = run(audio((500, 0), (1500, 0.5), (1000, 0)))
    assert [type(e) for e in events] == [SpeechStarted, SpeechEnded]
    assert 1.5 <= events[1].duration <= 2.6


def test_two_utterances_separated_by_long_pause():
    events = run(audio((1000, 0.5), (1000, 0), (1000, 0.5), (1000, 0)))
    assert [type(e) for e in events] == [SpeechStarted, SpeechEnded, SpeechStarted, SpeechEnded]


def test_short_pause_does_not_split_a_sentence():
    events = run(audio((800, 0.5), (400, 0), (800, 0.5), (1000, 0)))
    assert [type(e) for e in events] == [SpeechStarted, SpeechEnded]


@pytest.mark.parametrize("ms, started", [(200, False), (300, True)])
def test_minimum_speech_duration(ms, started):
    events = run(audio((ms, 0.5), (1000, 0)))
    assert (SpeechStarted() in events) is started


def test_silence_only():
    assert run(audio((5000, 0))) == []


def test_unfinished_speech_has_not_ended():
    assert run(audio((2000, 0.5))) == [SpeechStarted()]


def test_chunk_size_does_not_matter():
    stream = audio((300, 0), (1200, 0.5), (900, 0))
    durations = {round(run(stream, chunk_ms=ms)[-1].duration, 3) for ms in (10, 32, 100, 1000)}
    assert len(durations) == 1


def test_during_playback_brief_sounds_are_ignored():
    assert run(audio((350, 0.5), (1000, 0)), playback=True) == []
    assert SpeechStarted() in run(audio((600, 0.5), (1000, 0)), playback=True)
