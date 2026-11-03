"""Spec: English speech is transcribed by the English model, Telugu speech by the Telugu model,
and the transcript says which language was spoken."""

from types import SimpleNamespace

import numpy as np
import pytest

from digital_me.config import ListeningSettings
from digital_me.stt import BilingualTranscriber, Transcript


class Model:
    def __init__(self, text, language):
        self.text, self.language, self.ready = text, language, True

    def warm_up(self):
        pass

    def transcribe(self, audio):
        return Transcript(self.text, len(audio) / 16000, self.language)


@pytest.mark.parametrize(
    "probs, text, language",
    [
        ({"en": 0.97, "te": 0.01}, "What's your cat called?", "en"),
        ({"en": 0.02, "te": 0.95}, "మీ పిల్లి పేరు ఏమిటి?", "te"),
    ],
)
def test_routes_by_spoken_language(probs, text, language):
    detector = SimpleNamespace(detect_language=lambda audio: (None, None, list(probs.items())))
    transcriber = BilingualTranscriber(
        {"en": Model("What's your cat called?", "en"), "te": Model("మీ పిల్లి పేరు ఏమిటి?", "te")},
        detector_factory=lambda: detector,
    )
    result = transcriber.transcribe(np.zeros(32000))
    assert (result.text, result.language, result.duration) == (text, language, 2.0)


def test_both_languages_on_by_default():
    assert ListeningSettings().languages == ["en", "te"]
    assert ListeningSettings().telugu_model == "base"


@pytest.mark.parametrize("languages", [[], ["fr"], ["en", "hi"]])
def test_only_supported_languages_allowed(languages):
    with pytest.raises(ValueError):
        ListeningSettings(languages=languages)


def test_duplicate_languages_collapsed():
    assert ListeningSettings(languages=["te", "en", "te"]).languages == ["te", "en"]
