"""Real models: Telugu and English speech are told apart and transcribed in their own script.

Telugu test speech is generated locally with the MMS Telugu voice (no recordings needed).
Synthetic Telugu is harder than real speech, so the bar is "mostly right", not word-perfect.
"""

import numpy as np
import pytest

from digital_me.language import detect_language
from digital_me.stt import BilingualTranscriber, WhisperTranscriber, telugu_model
from digital_me.stt.whisper import _default_model_factory
from digital_me.tts import MmsEngine

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def bilingual():
    try:
        path = telugu_model.ensure_model("base")
    except Exception as exc:
        pytest.skip(f"Telugu model not available: {exc}")
    transcriber = BilingualTranscriber(
        {
            "en": WhisperTranscriber("base.en", "en"),
            "te": WhisperTranscriber("telugu-base", "te", model_factory=lambda _n: _default_model_factory(str(path))),
        }
    )
    transcriber.warm_up()
    return transcriber


@pytest.fixture(scope="module")
def say_telugu():
    engine = MmsEngine()
    engine.warm_up()
    return lambda text: engine.synthesize(text, "te_mms", 1.0).audio


def overlap(expected: str, heard: str) -> float:
    exp, got = expected.replace(".", "").split(), set(heard.replace(".", "").split())
    return sum(word in got for word in exp) / len(exp)


@pytest.mark.parametrize(
    "sentence",
    ["నా పిల్లి పేరు మిసో.", "మీరు ఎలా ఉన్నారు?", "నాకు సంగీతం అంటే చాలా ఇష్టం."],
)
def test_telugu_speech_understood_in_telugu(bilingual, say_telugu, sentence):
    result = bilingual.transcribe(say_telugu(sentence))
    assert result.language == "te"
    assert detect_language(result.text) == "te", result.text
    assert overlap(sentence, result.text) >= 0.5, result.text


@pytest.mark.parametrize("sentence", ["ఏం చేస్తున్నారు?", "ఎలా ఉన్నావు?", "శుభ రాత్రి.", "మీకు ఏ సంగీతం ఇష్టం?"])
def test_phrases_once_misheard_as_english_are_telugu(bilingual, say_telugu, sentence):
    """Regression: these came out as English nonsense ("E.M. Chest to Naru.")."""
    result = bilingual.transcribe(say_telugu(sentence))
    assert result.language == "te", result.text
    assert detect_language(result.text) == "te", result.text


@pytest.mark.parametrize("sentence", ["Okay.", "Good night.", "Tell me about your weekend."])
def test_short_english_stays_english(bilingual, say, sentence):
    result = bilingual.transcribe(say(sentence))
    assert result.language == "en", result.text
    assert detect_language(result.text) == "en", result.text


def test_english_speech_still_english(bilingual, say):
    result = bilingual.transcribe(say("What kind of music do you like?"))
    assert result.language == "en"
    assert "music" in result.text.lower()


def test_silence_gives_no_text(bilingual):
    assert bilingual.transcribe(np.zeros(32000, dtype=np.float32)).text == ""
