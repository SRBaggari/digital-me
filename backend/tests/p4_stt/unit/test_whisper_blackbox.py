"""Spec: audio in, clean text out (segments joined, whitespace trimmed); duration reported."""

from types import SimpleNamespace

import numpy as np

from digital_me.stt import WhisperTranscriber


def transcriber_returning(*texts):
    segments = [SimpleNamespace(text=t, no_speech_prob=0.0, avg_logprob=-0.1) for t in texts]
    model = SimpleNamespace(transcribe=lambda audio, **kw: (iter(segments), None))
    return WhisperTranscriber(model_factory=lambda name: model)


def test_segments_joined():
    result = transcriber_returning(" Hi,", "  how are you? ").transcribe(np.zeros(32000, dtype=np.float32))
    assert result.text == "Hi, how are you?"
    assert result.duration == 2.0


def test_no_speech_gives_empty_text():
    assert transcriber_returning().transcribe(np.zeros(8000)).text == ""


def test_accepts_any_numeric_shape():
    assert transcriber_returning(" ok").transcribe(np.zeros((1, 1600), dtype=np.float64)).text == "ok"
