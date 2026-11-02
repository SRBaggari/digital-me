import numpy as np
import pytest

from digital_me.stt import WhisperTranscriber
from digital_me.tts import KokoroEngine


def to_16k(audio: np.ndarray, rate: int) -> np.ndarray:
    n = int(len(audio) * 16_000 / rate)
    return np.interp(np.linspace(0, len(audio), n, endpoint=False), np.arange(len(audio)), audio).astype(np.float32)


@pytest.fixture(scope="session")
def say():
    """Real spoken audio at 16 kHz, generated locally by Kokoro (no recordings needed)."""
    engine = KokoroEngine()
    try:
        engine.warm_up()
    except Exception as exc:
        pytest.skip(f"Kokoro not available: {exc}")

    def speak(text: str, voice: str = "am_michael") -> np.ndarray:
        synthesis = engine.synthesize(text, voice, 1.0)
        return to_16k(synthesis.audio, synthesis.sample_rate)

    return speak


@pytest.fixture(scope="session")
def real_whisper():
    transcriber = WhisperTranscriber("base.en")
    try:
        transcriber.warm_up()
    except Exception as exc:
        pytest.skip(f"Whisper not available: {exc}")
    return transcriber
