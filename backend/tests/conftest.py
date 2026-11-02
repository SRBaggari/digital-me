"""Shared fixtures. Test classification is derived from file location and name:

    tests/<part>/unit/test_<feature>_whitebox.py         -> whitebox
    tests/<part>/integration/test_<feature>_blackbox.py  -> blackbox + integration
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import numpy as np
import pytest

from digital_me.config import instance as instance_module
from digital_me.llm import LLMError, LLMHealth, OllamaClient
from digital_me.stt import Transcript
from digital_me.tts import Synthesis, TTSError, Voice, WordTiming


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        stem = item.path.stem
        if stem.endswith("_whitebox"):
            item.add_marker(pytest.mark.whitebox)
        elif stem.endswith("_blackbox"):
            item.add_marker(pytest.mark.blackbox)
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def instances_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty, private instances directory for one test."""
    home = tmp_path / "instances"
    monkeypatch.setenv(instance_module.HOME_ENV_VAR, str(home))
    return home


@pytest.fixture
def template_dir() -> Path:
    return instance_module.TEMPLATE_DIR


LIVE_MODEL = os.environ.get("DIGITAL_ME_TEST_MODEL", "llama3.2:3b")


@pytest.fixture
async def live_llm():
    """A real local Ollama client; the test is skipped if Ollama or the model is unavailable."""
    client = OllamaClient("http://127.0.0.1:11434", LIVE_MODEL, timeout=180)
    health = await client.health()
    if not (health.reachable and health.model_available):
        pytest.skip(f"Ollama with {LIVE_MODEL} not available: {health.detail}")
    return client


class FakeLLM:
    """Scripted LLM: yields the given chunks, optionally failing after `fail_after` chunks."""

    model = "fake"

    def __init__(self, chunks: list[str] | None = None, *, fail_after: int | None = None,
                 error: Exception | None = None, delay: float = 0.0):
        self.chunks = chunks if chunks is not None else ["[neutral] Hello there."]
        self.fail_after = fail_after
        self.error = error or LLMError("boom")
        self.delay = delay
        self.calls: list[dict] = []

    async def stream_chat(self, messages, *, temperature, num_ctx):
        self.calls.append({"messages": messages, "temperature": temperature, "num_ctx": num_ctx})
        for i, chunk in enumerate(self.chunks):
            if self.fail_after is not None and i == self.fail_after:
                raise self.error
            if self.delay:
                await asyncio.sleep(self.delay)
            yield chunk
        if self.fail_after is not None and self.fail_after >= len(self.chunks):
            raise self.error

    async def health(self) -> LLMHealth:
        return LLMHealth(reachable=True, model_available=True)


@pytest.fixture
def fake_llm_factory():
    return FakeLLM


class FakeTTS:
    """Deterministic engine: 0.1 s of audio per word, one WordTiming per word."""

    name = "fake"
    sample_rate = 1000

    def __init__(self, *, fail_on: str | None = None, delay: float = 0.0):
        self.fail_on = fail_on
        self.delay = delay
        self.calls: list[tuple[str, str, float]] = []
        self.warmed = False

    @property
    def ready(self) -> bool:
        return self.warmed

    def voices(self):
        return [Voice("v1", "One", "American", "female"), Voice("v2", "Two", "British", "male")]

    def warm_up(self, voice: str = "v1") -> None:
        self.warmed = True

    def synthesize(self, text: str, voice: str, speed: float) -> Synthesis:
        self.calls.append((text, voice, speed))
        if self.delay:
            time.sleep(self.delay)
        if self.fail_on and self.fail_on in text:
            raise TTSError("synthesis broke")
        words = text.split()
        step = 0.1 / speed
        timings = [WordTiming(w, round(i * step, 3), round((i + 1) * step, 3)) for i, w in enumerate(words)]
        audio = np.full(int(len(words) * step * self.sample_rate), 0.25, dtype=np.float32)
        return Synthesis(audio, self.sample_rate, timings)


@pytest.fixture
def fake_tts_factory():
    return FakeTTS


class FakeTranscriber:
    """Returns scripted texts in order (default: 'hello there')."""

    name = "fake-stt"

    def __init__(self, texts=None, *, error: Exception | None = None, delay: float = 0.0):
        self.texts = list(texts) if texts is not None else []
        self.error = error
        self.delay = delay
        self.received: list[np.ndarray] = []
        self.warmed = False

    @property
    def ready(self) -> bool:
        return self.warmed

    def warm_up(self) -> None:
        self.warmed = True

    def transcribe(self, audio):
        self.received.append(audio)
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        text = self.texts.pop(0) if self.texts else "hello there"
        return Transcript(text=text, duration=len(audio) / 16_000)


def loudness_vad():
    """VAD stand-in: a frame is speech when it is loud."""
    return lambda frame: 1.0 if float(np.abs(frame).mean()) > 0.1 else 0.0


def pcm(ms: int, amplitude: float = 0.0) -> bytes:
    """16 kHz 16-bit PCM: amplitude 0 = silence, 0.5 = 'speech' for loudness_vad."""
    return (np.full(16 * ms, amplitude, dtype=np.float32) * 32767).astype("<i2").tobytes()


@pytest.fixture
def fake_transcriber_factory():
    return FakeTranscriber


@pytest.fixture
def speech_audio():
    """Helpers to build microphone streams: speech_audio.voice(ms), speech_audio.silence(ms)."""

    class Audio:
        voice = staticmethod(lambda ms: pcm(ms, 0.5))
        silence = staticmethod(lambda ms: pcm(ms, 0.0))
        vad = staticmethod(loudness_vad)

    return Audio
