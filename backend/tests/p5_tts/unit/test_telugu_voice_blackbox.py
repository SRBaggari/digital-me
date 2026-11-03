"""Spec: English sentences are spoken by the English voice, Telugu ones by the Telugu voice;
text without letters goes to the default (English) voice."""

import numpy as np
import pytest

from digital_me.tts import LanguageRouter, Synthesis, Voice


class Engine:
    def __init__(self, name):
        self.name = name
        self.spoken = []
        self.ready = True

    def voices(self):
        return [Voice(f"{self.name}1", self.name, self.name, "")]

    def warm_up(self, voice=None):
        pass

    def synthesize(self, text, voice, speed):
        self.spoken.append(text)
        return Synthesis(np.zeros(100, dtype=np.float32), 1000)


@pytest.mark.parametrize(
    "text, engine",
    [
        ("Hi! How are you?", "en"),
        ("నేను బాగున్నాను.", "te"),
        ("నాకు jazz అంటే ఇష్టం.", "te"),
        ("42", "en"),
    ],
)
def test_each_sentence_goes_to_its_language(text, engine):
    engines = {"en": Engine("en"), "te": Engine("te")}
    LanguageRouter(engines).synthesize(text, "en1", 1.0)
    assert engines[engine].spoken == [text]


def test_unsupported_language_uses_default():
    engines = {"en": Engine("en")}
    LanguageRouter(engines).synthesize("నమస్కారం", "en1", 1.0)
    assert engines["en"].spoken == ["నమస్కారం"]


def test_ready_only_when_all_engines_ready():
    en, te = Engine("en"), Engine("te")
    te.ready = False
    assert not LanguageRouter({"en": en, "te": te}).ready
