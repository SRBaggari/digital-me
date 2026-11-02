from types import SimpleNamespace

import numpy as np
import pytest

from digital_me.stt import STTError, WhisperTranscriber
from digital_me.stt import whisper as w


class FakeWhisperModel:
    def __init__(self, segments=None, error=None):
        self.segments = segments or [SimpleNamespace(text=" Hello.", no_speech_prob=0.01, avg_logprob=-0.2)]
        self.error = error
        self.kwargs = None

    def transcribe(self, audio, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return iter(self.segments), SimpleNamespace(language="en")


def test_decoding_options():
    model = FakeWhisperModel()
    WhisperTranscriber("base.en", "en", model_factory=lambda name: model).transcribe(np.zeros(16000))
    assert model.kwargs["language"] == "en"
    assert model.kwargs["beam_size"] == 1
    assert model.kwargs["vad_filter"] is False
    assert model.kwargs["condition_on_previous_text"] is False


def test_model_loaded_lazily_once():
    loads = []
    transcriber = WhisperTranscriber("small.en", model_factory=lambda name: loads.append(name) or FakeWhisperModel())
    assert not transcriber.ready
    transcriber.transcribe(np.zeros(100))
    transcriber.transcribe(np.zeros(100))
    assert loads == ["small.en"] and transcriber.ready


def test_low_confidence_noise_segments_dropped():
    segments = [
        SimpleNamespace(text=" Thank you.", no_speech_prob=0.9, avg_logprob=-1.5),  # hallucinated
        SimpleNamespace(text=" Real words.", no_speech_prob=0.9, avg_logprob=-0.3),  # confident: kept
        SimpleNamespace(text=" More.", no_speech_prob=0.1, avg_logprob=-1.4),  # speech likely: kept
    ]
    transcriber = WhisperTranscriber(model_factory=lambda name: FakeWhisperModel(segments))
    assert transcriber.transcribe(np.zeros(100)).text == "Real words. More."


def test_library_errors_wrapped():
    transcriber = WhisperTranscriber(model_factory=lambda name: FakeWhisperModel(error=RuntimeError("bad")))
    with pytest.raises(STTError, match="bad"):
        transcriber.transcribe(np.zeros(100))


def test_load_errors_wrapped():
    def broken(name):
        raise OSError("disk")

    with pytest.raises(STTError, match="disk"):
        WhisperTranscriber(model_factory=broken).transcribe(np.zeros(100))


def test_default_factory_tries_cache_first(monkeypatch):
    calls = []

    class Recorder:
        def __init__(self, name, **kwargs):
            calls.append(kwargs.get("local_files_only", False))
            if kwargs.get("local_files_only"):
                raise OSError("not cached")

    monkeypatch.setattr("faster_whisper.WhisperModel", Recorder)
    w._default_model_factory("base.en")
    assert calls == [True, False]
