"""Real SYSPIN model: loads offline from cache and keeps up with speech in real time."""

import time

import pytest

from digital_me.tts import SyspinEngine
from digital_me.tts import syspin_engine

pytestmark = pytest.mark.live


def test_model_files_resolve_from_cache_without_network(monkeypatch):
    import huggingface_hub

    attempts = []
    original = huggingface_hub.hf_hub_download

    def recording(**kwargs):
        attempts.append(kwargs.get("local_files_only", False))
        return original(**kwargs)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", recording)
    syspin_engine.fetch(syspin_engine.MODEL_FILE)
    assert attempts == [True]


def test_faster_than_real_time():
    engine = SyspinEngine()
    engine.warm_up()
    start = time.perf_counter()
    synthesis = engine.synthesize("నాకు జాజ్ సంగీతం అంటే చాలా ఇష్టం, అది చాలా ప్రశాంతంగా ఉంటుంది.", "te_female", 1.0)
    assert time.perf_counter() - start < synthesis.duration
