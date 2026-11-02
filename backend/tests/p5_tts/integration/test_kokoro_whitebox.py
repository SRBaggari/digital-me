"""Real Kokoro model on CPU: internal properties of what it returns."""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.live


def test_audio_is_finite_float32_in_range(real_kokoro):
    audio = real_kokoro.synthesize("Testing one two three.", "af_heart", 1.0).audio
    assert audio.dtype == np.float32
    assert np.isfinite(audio).all()
    assert np.abs(audio).max() <= 1.0


def test_british_pipeline_loaded_separately(real_kokoro):
    real_kokoro.synthesize("Lovely weather.", "bf_emma", 1.0)
    assert {"a", "b"} <= set(real_kokoro._pipelines)


@pytest.mark.parametrize("filename", ["config.json", "kokoro-v1_0.pth", "voices/af_heart.pt"])
def test_cached_files_resolve_without_network(real_kokoro, filename):
    from huggingface_hub import hf_hub_download

    from digital_me.tts.kokoro_engine import fetch

    attempts = []

    def recording_download(**kwargs):
        attempts.append(kwargs.get("local_files_only", False))
        return hf_hub_download(**kwargs)

    assert os.path.isfile(fetch(filename, recording_download))
    assert attempts == [True]  # answered from the cache; no network attempt


def test_both_accents_share_one_model(real_kokoro):
    real_kokoro.synthesize("Hi.", "af_heart", 1.0)
    real_kokoro.synthesize("Hi.", "bm_george", 1.0)
    assert real_kokoro._pipelines["a"].model is real_kokoro._pipelines["b"].model
