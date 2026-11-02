"""Spec: audio is delivered as standard 16-bit mono WAV that any decoder can read back."""

import base64
import io
import wave

import numpy as np
import pytest

from digital_me.tts import to_wav_base64, to_wav_bytes


@pytest.mark.parametrize("n, rate", [(0, 24_000), (1, 8000), (24_000, 24_000)])
def test_round_trip_with_standard_decoder(n, rate):
    audio = np.linspace(-1, 1, n, dtype=np.float32)
    with wave.open(io.BytesIO(to_wav_bytes(audio, rate))) as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == rate
        assert wav.getnframes() == n


def test_base64_is_the_same_wav():
    audio = np.zeros(100, dtype=np.float32)
    assert base64.b64decode(to_wav_base64(audio, 16_000)) == to_wav_bytes(audio, 16_000)
