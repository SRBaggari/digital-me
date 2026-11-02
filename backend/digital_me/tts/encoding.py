"""Audio encoding for the browser."""

from __future__ import annotations

import base64
import io
import wave

import numpy as np


def to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Mono float32 [-1, 1] -> 16-bit PCM WAV."""
    samples = np.clip(np.asarray(audio, dtype=np.float32).reshape(-1), -1.0, 1.0)
    pcm = (samples * 32767.0).round().astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()


def to_wav_base64(audio: np.ndarray, sample_rate: int) -> str:
    return base64.b64encode(to_wav_bytes(audio, sample_rate)).decode("ascii")
