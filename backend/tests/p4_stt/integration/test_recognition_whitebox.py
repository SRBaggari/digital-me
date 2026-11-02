"""Real models: internal properties (timing, model state, cache use)."""

import time

import numpy as np
import pytest

from digital_me.stt import FRAME, SileroVAD, SpeechDetector, SpeechEnded, SpeechStarted

pytestmark = pytest.mark.live


def test_vad_is_fast_enough_for_real_time(say):
    vad = SileroVAD()
    audio = say("Testing the speed of voice detection on this computer.")
    frames = [audio[i : i + FRAME] for i in range(0, len(audio) - FRAME, FRAME)]
    start = time.perf_counter()
    for frame in frames:
        vad(frame)
    per_frame_ms = (time.perf_counter() - start) * 1000 / len(frames)
    assert per_frame_ms < 32 / 2  # must keep up with 32 ms frames with plenty of margin


def test_vad_probability_separates_speech_from_silence(say):
    vad = SileroVAD()
    speech = say("Good morning, how are you?")
    speech_probs = [vad(speech[i : i + FRAME]) for i in range(0, len(speech) - FRAME, FRAME)]
    vad.reset()
    silence_probs = [vad(np.zeros(FRAME, dtype=np.float32)) for _ in range(30)]
    assert max(speech_probs) > 0.9
    assert max(silence_probs) < 0.2


def test_utterance_keeps_pre_roll_so_first_word_is_not_clipped(say):
    speech = say("Hello.")
    stream = np.concatenate([np.zeros(16_000, dtype=np.float32), speech, np.zeros(16_000, dtype=np.float32)])
    events = SpeechDetector(SileroVAD()).feed(stream)
    assert isinstance(events[0], SpeechStarted)
    ended = next(e for e in events if isinstance(e, SpeechEnded))
    assert ended.duration > len(speech) / 16_000  # speech plus padding around it


def test_whisper_loads_from_cache_without_network(real_whisper, monkeypatch):
    from digital_me.stt import whisper

    attempts = []

    import faster_whisper

    original = faster_whisper.WhisperModel

    def recording(name, **kwargs):
        attempts.append(kwargs.get("local_files_only", False))
        return original(name, **kwargs)

    monkeypatch.setattr(faster_whisper, "WhisperModel", recording)
    whisper._default_model_factory("base.en")
    assert attempts == [True]
