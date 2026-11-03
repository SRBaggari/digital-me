from types import SimpleNamespace

import numpy as np
import pytest

from digital_me.stt import BilingualTranscriber, STTError, Transcript
from digital_me.stt import telugu_model


class FakeWhisper:
    def __init__(self, text, language):
        self.text = text
        self.language = language
        self.ready = False
        self.heard = 0

    def warm_up(self):
        self.ready = True

    def transcribe(self, audio):
        self.heard += 1
        return Transcript(self.text, 1.0, self.language)


def detector(probs):
    calls = []
    model = SimpleNamespace(detect_language=lambda audio: calls.append(1) or ("xx", 0.9, list(probs.items())))
    return model, calls


def bilingual(probs):
    model, calls = detector(probs)
    en, te = FakeWhisper("hello", "en"), FakeWhisper("నమస్కారం", "te")
    return BilingualTranscriber({"en": en, "te": te}, detector_factory=lambda: model), en, te, calls


def test_unsupported_top_language_is_ignored():
    # Telugu speech is often confused with Kannada/Tamil; only the supported pair is compared.
    transcriber, en, te, _ = bilingual({"kn": 0.6, "te": 0.3, "en": 0.05})
    assert transcriber.detect(np.zeros(100)) == "te"


def test_any_non_english_top_guess_means_telugu():
    # measured: Telugu speech is often guessed as Hindi, Tamil, Japanese, Korean...
    for top in ["hi", "ta", "ja", "ko", "fr"]:
        transcriber, *_ = bilingual({top: 0.4, "en": 0.3, "te": 0.05})
        assert transcriber.detect(np.zeros(100)) == "te", top


def test_english_top_guess_means_english():
    transcriber, *_ = bilingual({"en": 0.5, "hi": 0.3, "te": 0.2})
    assert transcriber.detect(np.zeros(100)) == "en"


class ScoredWhisper(FakeWhisper):
    def __init__(self, text, language, confidence):
        super().__init__(text, language)
        self.confidence = confidence

    def transcribe(self, audio):
        self.heard += 1
        return Transcript(self.text, 1.0, self.language, self.confidence)


def scored(probs, en_confidence):
    model, _ = detector(probs)
    en = ScoredWhisper("E.M. Chest to Naru.", "en", en_confidence)
    te = ScoredWhisper("ఏం చేస్తున్నారు", "te", -0.01)
    return BilingualTranscriber({"en": en, "te": te}, detector_factory=lambda: model), en, te


def test_hesitant_english_with_garbled_transcript_is_retried_as_telugu():
    transcriber, en, te = scored({"en": 0.45, "hi": 0.3}, en_confidence=-0.9)
    result = transcriber.transcribe(np.zeros(100))
    assert (result.text, result.language) == ("ఏం చేస్తున్నారు", "te")
    assert en.heard == 1 and te.heard == 1


def test_confident_english_detection_is_kept_even_if_transcript_is_unsure():
    # "Okay" scored -0.88 in the English model but the detector was 81-85% sure of English
    transcriber, en, te = scored({"en": 0.85}, en_confidence=-0.9)
    assert transcriber.transcribe(np.zeros(100)).language == "en"
    assert te.heard == 0


def test_hesitant_english_with_clear_transcript_is_kept():
    transcriber, en, te = scored({"en": 0.45, "hi": 0.3}, en_confidence=-0.2)
    assert transcriber.transcribe(np.zeros(100)).language == "en"
    assert te.heard == 0


def test_single_language_skips_detection():
    calls = []
    transcriber = BilingualTranscriber(
        {"en": FakeWhisper("hi", "en")}, detector_factory=lambda: calls.append(1)
    )
    assert transcriber.detect(np.zeros(100)) == "en"
    assert calls == []


def test_detector_loaded_lazily_once():
    loads = []
    model, _ = detector({"en": 1.0})
    transcriber = BilingualTranscriber(
        {"en": FakeWhisper("a", "en"), "te": FakeWhisper("b", "te")},
        detector_factory=lambda: loads.append(1) or model,
    )
    transcriber.transcribe(np.zeros(100))
    transcriber.transcribe(np.zeros(100))
    assert loads == [1]


def test_detector_errors_wrapped():
    def broken():
        raise OSError("missing")

    transcriber = BilingualTranscriber(
        {"en": FakeWhisper("a", "en"), "te": FakeWhisper("b", "te")}, detector_factory=broken
    )
    with pytest.raises(STTError, match="language"):
        transcriber.transcribe(np.zeros(100))


def test_warm_up_loads_everything():
    transcriber, en, te, calls = bilingual({"en": 1.0})
    transcriber.warm_up()
    assert en.ready and te.ready and calls and transcriber.ready


def test_needs_at_least_one_language():
    with pytest.raises(ValueError):
        BilingualTranscriber({})


def test_telugu_model_ready_needs_weights_and_tokenizer(tmp_path):
    path = telugu_model.model_dir("base", tmp_path)
    path.mkdir(parents=True)
    (path / "model.bin").write_bytes(b"x")
    assert not telugu_model.is_ready(path)
    (path / "tokenizer.json").write_text("{}")
    assert telugu_model.is_ready(path)


def test_ensure_model_does_nothing_when_already_converted(tmp_path, monkeypatch):
    path = telugu_model.model_dir("small", tmp_path)
    path.mkdir(parents=True)
    (path / "model.bin").write_bytes(b"x")
    (path / "tokenizer.json").write_text("{}")
    monkeypatch.setattr("ctranslate2.converters.TransformersConverter", None)  # would crash if used
    assert telugu_model.ensure_model("small", tmp_path) == path


def test_model_dir_names():
    assert telugu_model.model_dir("base").name == "whisper-telugu-base-ct2"
    assert telugu_model.MODELS_DIR.name == "models"
