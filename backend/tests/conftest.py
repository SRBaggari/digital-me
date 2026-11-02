"""Shared fixtures. Test classification is derived from file location and name:

    tests/<part>/unit/test_<feature>_whitebox.py         -> whitebox
    tests/<part>/integration/test_<feature>_blackbox.py  -> blackbox + integration
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from digital_me.config import instance as instance_module
from digital_me.llm import LLMError, LLMHealth, OllamaClient


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
