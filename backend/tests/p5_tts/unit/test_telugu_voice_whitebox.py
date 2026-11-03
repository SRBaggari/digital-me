from types import SimpleNamespace

import numpy as np
import pytest
import torch

from digital_me.tts import LanguageRouter, MmsEngine, TTSError
from digital_me.tts.mms_engine import VOICE


class FakeVits:
    def __init__(self):
        self.config = SimpleNamespace(sampling_rate=16_000)
        self.speaking_rate = 1.0
        self.calls = []

    def __call__(self, input_ids):
        self.calls.append((input_ids.shape[-1], self.speaking_rate))
        return SimpleNamespace(waveform=torch.full((1, 800 * input_ids.shape[-1]), 0.1))


def fake_tokenizer(text, return_tensors):
    ids = [ord(c) for c in text if 0x0C00 <= ord(c) <= 0x0C7F]  # like MMS: drops other scripts
    return {"input_ids": torch.tensor([ids], dtype=torch.long)}


def make_mms():
    model = FakeVits()
    loads = []
    engine = MmsEngine(loader=lambda: loads.append(1) or (model, fake_tokenizer))
    return engine, model, loads


def test_speed_sets_speaking_rate():
    engine, model, _ = make_mms()
    engine.synthesize("నమస్కారం", VOICE.id, 1.4)
    assert model.calls[0][1] == 1.4


def test_loaded_lazily_once():
    engine, _, loads = make_mms()
    assert not engine.ready
    engine.synthesize("నమస్కారం", VOICE.id, 1.0)
    engine.synthesize("నమస్కారం", VOICE.id, 1.0)
    assert loads == [1] and engine.ready


def test_text_with_nothing_speakable_gives_silence():
    engine, model, _ = make_mms()
    assert engine.synthesize("Pixel.", VOICE.id, 1.0).duration == 0
    assert model.calls == []


def test_errors_wrapped():
    engine = MmsEngine(loader=lambda: (_ for _ in ()).throw(OSError("no model")))
    with pytest.raises(TTSError, match="no model"):
        engine.synthesize("నమస్కారం", VOICE.id, 1.0)


class Recorder:
    def __init__(self, name):
        self.name = name
        self.calls = []
        self.warmed = []
        self.ready = True

    def voices(self):
        from digital_me.tts import Voice

        return [Voice(f"{self.name}_voice", self.name, "x", "")]

    def warm_up(self, voice=None):
        self.warmed.append(voice)

    def synthesize(self, text, voice, speed):
        self.calls.append((text, voice, speed))
        from digital_me.tts import Synthesis

        return Synthesis(np.zeros(10, dtype=np.float32), 1000)


def test_router_uses_chosen_voice_only_for_default_language():
    en, te = Recorder("en"), Recorder("te")
    router = LanguageRouter({"en": en, "te": te})
    router.synthesize("Hello there.", "af_bella", 1.2)
    router.synthesize("నమస్కారం.", "af_bella", 1.2)
    assert en.calls == [("Hello there.", "af_bella", 1.2)]
    assert te.calls == [("నమస్కారం.", "te_voice", 1.2)]  # own voice, same speed


def test_router_warms_every_engine_with_the_right_voice():
    en, te = Recorder("en"), Recorder("te")
    LanguageRouter({"en": en, "te": te}).warm_up("bm_george")
    assert en.warmed == ["bm_george"] and te.warmed == [None]


def test_router_requires_default_engine():
    with pytest.raises(ValueError):
        LanguageRouter({"te": Recorder("te")})


def test_router_name_and_voices_come_from_engines():
    router = LanguageRouter({"en": Recorder("en"), "te": Recorder("te")})
    assert router.name == "en+te"
    assert [v.id for v in router.voices()] == ["en_voice"]
