from types import SimpleNamespace

import numpy as np
import pytest

from digital_me.tts import KokoroEngine


def token(text, start, end, phonemes="x"):
    return SimpleNamespace(text=text, start_ts=start, end_ts=end, phonemes=phonemes)


def result(seconds, tokens):
    return SimpleNamespace(audio=np.full(int(seconds * 24_000), 0.1, dtype=np.float32), tokens=tokens)


class FakePipeline:
    """Imitates kokoro.KPipeline: calling it yields result chunks."""

    def __init__(self, code, results=None, error=None):
        self.code = code
        self.results = results if results is not None else [result(0.5, [token("Hi", 0.1, 0.3)])]
        self.error = error
        self.calls = []

    def __call__(self, text, voice, speed):
        self.calls.append((text, voice, speed))
        if self.error:
            raise self.error
        yield from self.results


@pytest.fixture
def pipelines():
    return {}


@pytest.fixture
def make_kokoro(pipelines):
    def make(results=None, error=None):
        def factory(code):
            pipelines[code] = FakePipeline(code, results, error)
            return pipelines[code]

        return KokoroEngine(pipeline_factory=factory, voice_path=lambda voice: voice)

    return make


@pytest.fixture
def fake_token():
    return token


@pytest.fixture
def fake_result():
    return result


@pytest.fixture(scope="session")
def real_kokoro():
    """The real model (downloaded once, then loaded from the local cache)."""
    engine = KokoroEngine()
    try:
        engine.warm_up()
    except Exception as exc:  # e.g. first run without internet
        pytest.skip(f"Kokoro not available: {exc}")
    return engine
