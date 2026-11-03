"""Spec: a female instance only offers female voices, and a male voice chosen earlier is replaced."""

import numpy as np

from digital_me.tts import LanguageRouter, Synthesis, Voice


class Catalog:
    name = "catalog"
    ready = True

    def __init__(self):
        self.used = []

    def voices(self):
        return [Voice("af_heart", "Heart", "American", "female"), Voice("am_michael", "Michael", "American", "male"),
                Voice("bf_emma", "Emma", "British", "female")]

    def warm_up(self, voice=None):
        pass

    def synthesize(self, text, voice, speed):
        self.used.append(voice)
        return Synthesis(np.zeros(10, dtype=np.float32), 1000)


def test_only_female_voices_offered():
    router = LanguageRouter({"en": Catalog()}, gender="female")
    assert [v.id for v in router.voices()] == ["af_heart", "bf_emma"]


def test_male_voice_chosen_earlier_is_replaced_by_a_female_one():
    engine = Catalog()
    router = LanguageRouter({"en": engine}, gender="female")
    router.synthesize("Hello.", "am_michael", 1.0)
    assert engine.used == ["af_heart"]
    assert router.effective_voice("am_michael") == "af_heart"
    assert router.effective_voice("bf_emma") == "bf_emma"


def test_without_gender_everything_is_offered():
    assert len(LanguageRouter({"en": Catalog()}).voices()) == 3
