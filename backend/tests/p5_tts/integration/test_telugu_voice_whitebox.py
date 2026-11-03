"""Real MMS Telugu model: internal properties."""

import time

import numpy as np
import pytest

from digital_me.tts import MmsEngine
from digital_me.tts import mms_engine

pytestmark = pytest.mark.live


def test_loads_from_cache_without_network(monkeypatch):
    import transformers

    attempts = []
    original = transformers.VitsModel.from_pretrained.__func__

    def recording(cls, repo, **kwargs):
        attempts.append(kwargs.get("local_files_only", False))
        return original(cls, repo, **kwargs)

    monkeypatch.setattr(transformers.VitsModel, "from_pretrained", classmethod(recording))
    mms_engine._default_loader()
    assert attempts == [True]


def test_faster_than_real_time_on_cpu():
    engine = MmsEngine()
    engine.warm_up()
    start = time.perf_counter()
    synthesis = engine.synthesize("నాకు రాక్ క్లైంబింగ్ అంటే చాలా ఇష్టం, ఫోటోలు తీస్తాను.", "te_mms", 1.0)
    assert time.perf_counter() - start < synthesis.duration


def test_audio_is_finite_and_in_range():
    audio = MmsEngine().synthesize("నమస్కారం.", "te_mms", 1.0).audio
    assert audio.dtype == np.float32 and np.isfinite(audio).all() and np.abs(audio).max() <= 1.5
