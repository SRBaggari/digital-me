import struct

import numpy as np

from digital_me.tts import to_wav_bytes


def test_header_fields():
    wav = to_wav_bytes(np.zeros(10, dtype=np.float32), 24_000)
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"
    channels, rate = struct.unpack("<HI", wav[22:28])
    bits = struct.unpack("<H", wav[34:36])[0]
    assert (channels, rate, bits) == (1, 24_000, 16)


def test_samples_are_clipped_and_scaled():
    wav = to_wav_bytes(np.array([2.0, -2.0, 0.5], dtype=np.float32), 8000)
    samples = struct.unpack("<3h", wav[-6:])
    assert samples == (32767, -32767, 16384)


def test_2d_input_flattened():
    wav = to_wav_bytes(np.zeros((1, 5), dtype=np.float32), 8000)
    assert len(wav) == 44 + 10
