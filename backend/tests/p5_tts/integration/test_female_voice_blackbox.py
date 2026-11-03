"""Real SYSPIN female Telugu voice: produces clear Telugu speech that recognition understands."""

import numpy as np
import pytest

from digital_me.tts import SyspinEngine

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def female():
    engine = SyspinEngine()
    try:
        engine.warm_up()
    except Exception as exc:
        pytest.skip(f"Female Telugu voice not available: {exc}")
    return engine


def test_speaks_telugu(female):
    synthesis = female.synthesize("నా పిల్లి పేరు మిసో.", "te_female", 1.0)
    assert synthesis.sample_rate == 22_050
    assert 0.8 < synthesis.duration < 5
    assert np.isfinite(synthesis.audio).all()


def test_is_understood_by_telugu_speech_recognition(female):
    from digital_me.stt import WhisperTranscriber, telugu_model
    from digital_me.stt.whisper import _default_model_factory

    path = telugu_model.ensure_model("base")
    recogniser = WhisperTranscriber("te", "te", model_factory=lambda _n: _default_model_factory(str(path)))
    audio = female.synthesize("నాకు సంగీతం అంటే చాలా ఇష్టం.", "te_female", 1.0).audio
    audio16 = np.interp(np.linspace(0, len(audio), int(len(audio) * 16000 / 22050), endpoint=False),
                        np.arange(len(audio)), audio).astype(np.float32)
    heard = recogniser.transcribe(audio16).text
    assert "సంగీతం" in heard and "ఇష్టం" in heard, heard
