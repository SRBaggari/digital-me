import numpy as np
import pytest
import torch

from digital_me.tts import SyspinEngine, TTSError
from digital_me.tts.syspin_engine import BLANK, PAD, PUNCTUATIONS, VOICE, Tokenizer, _change_speed

LETTERS = "నాపిల్"


def test_vocabulary_layout_matches_training():
    # Coqui VitsCharacters: [pad] + punctuations + letters + [blank]
    tokenizer = Tokenizer(LETTERS)
    assert tokenizer._ids[PAD] == 0
    assert tokenizer._ids["!"] == 1
    assert tokenizer._ids[LETTERS[0]] == 1 + len(PUNCTUATIONS)
    assert tokenizer._ids[BLANK] == 1 + len(PUNCTUATIONS) + len(LETTERS)


def test_blank_between_every_character():
    tokenizer = Tokenizer(LETTERS)
    ids = tokenizer.encode("నా")
    assert ids[::2] == [tokenizer.blank_id] * 3 and len(ids) == 5


def test_cleaning_and_unknown_characters():
    tokenizer = Tokenizer(LETTERS)
    assert Tokenizer.clean('  "నా" ; పి-లి  ') == "నా , పి లి"
    assert tokenizer.encode("Pixel") == []  # Latin letters cannot be spoken by this voice


def test_speed_is_applied_within_a_natural_range():
    audio = np.arange(1000, dtype=np.float32)
    assert len(_change_speed(audio, 1.0)) == 1000
    assert len(_change_speed(audio, 1.1)) == pytest.approx(1000 / 1.1, abs=1)
    assert len(_change_speed(audio, 2.0)) == len(_change_speed(audio, 1.15))  # clamped


class FakeNet:
    def __call__(self, ids):
        return torch.full((1, 1, ids.shape[-1] * 100), 0.2)


def test_synthesis_uses_the_loaded_model():
    engine = SyspinEngine(loader=lambda: (FakeNet(), Tokenizer(LETTERS)))
    synthesis = engine.synthesize("నా పిల్లి", VOICE.id, 1.0)
    assert synthesis.sample_rate == 22_050 and synthesis.duration > 0


def test_nothing_speakable_gives_silence():
    engine = SyspinEngine(loader=lambda: (FakeNet(), Tokenizer(LETTERS)))
    assert engine.synthesize("Pixel", VOICE.id, 1.0).duration == 0


def test_load_errors_wrapped():
    def broken():
        raise OSError("no file")

    with pytest.raises(TTSError, match="no file"):
        SyspinEngine(loader=broken).synthesize("నా", VOICE.id, 1.0)


def test_voice_is_female():
    assert SyspinEngine().voices() == [VOICE] and VOICE.gender == "female"
