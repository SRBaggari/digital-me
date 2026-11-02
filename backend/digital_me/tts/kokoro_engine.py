"""Kokoro-82M (Apache-2.0): natural built-in voices, runs faster than real time on CPU."""

from __future__ import annotations

import logging
import os
import threading
import warnings
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import numpy as np

from .base import Synthesis, TTSError, Voice, WordTiming

log = logging.getLogger(__name__)

REPO_ID = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24_000

# A curated subset of Kokoro's English voices (the better-rated ones).
VOICES: list[Voice] = [
    Voice("af_heart", "Heart", "American", "female"),
    Voice("af_bella", "Bella", "American", "female"),
    Voice("af_nicole", "Nicole", "American", "female"),
    Voice("af_sarah", "Sarah", "American", "female"),
    Voice("am_michael", "Michael", "American", "male"),
    Voice("am_fenrir", "Fenrir", "American", "male"),
    Voice("am_puck", "Puck", "American", "male"),
    Voice("am_echo", "Echo", "American", "male"),
    Voice("bf_emma", "Emma", "British", "female"),
    Voice("bf_isabella", "Isabella", "British", "female"),
    Voice("bm_george", "George", "British", "male"),
    Voice("bm_fable", "Fable", "British", "male"),
]
VOICE_IDS = frozenset(v.id for v in VOICES)


def lang_code(voice_id: str) -> str:
    """Kokoro pipelines are per language: 'a' American English, 'b' British English."""
    return voice_id[0]


@contextmanager
def _hf_offline(enabled: bool):
    """Prefer the local model cache so normal runs make no network requests."""
    previous = os.environ.get("HF_HUB_OFFLINE")
    if enabled:
        os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous


def _default_pipeline_factory(code: str) -> Any:
    from kokoro import KPipeline  # heavy import, deferred

    return KPipeline(lang_code=code, repo_id=REPO_ID)


class KokoroEngine:
    name = "kokoro"

    def __init__(self, pipeline_factory: Callable[[str], Any] = _default_pipeline_factory):
        self._factory = pipeline_factory
        self._pipelines: dict[str, Any] = {}
        self._lock = threading.Lock()  # Kokoro pipelines are not thread-safe

    @property
    def ready(self) -> bool:
        return bool(self._pipelines)

    def voices(self) -> list[Voice]:
        return list(VOICES)

    def warm_up(self, voice: str = "af_heart") -> None:
        self.synthesize("Hello.", voice, 1.0)

    def synthesize(self, text: str, voice: str, speed: float) -> Synthesis:
        if voice not in VOICE_IDS:
            raise TTSError(f"Unknown voice {voice!r}")
        text = text.strip()
        if not text:
            return Synthesis(np.zeros(0, dtype=np.float32), SAMPLE_RATE)
        with self._lock:
            try:
                return self._run(text, voice, speed)
            except TTSError:
                raise
            except Exception as exc:  # model/library errors become one clear error type
                log.exception("Kokoro synthesis failed")
                raise TTSError(f"Speech synthesis failed: {exc}") from exc

    def _pipeline(self, code: str) -> Any:
        if code not in self._pipelines:
            self._pipelines[code] = self._offline_first(lambda: self._factory(code))
        return self._pipelines[code]

    def _run(self, text: str, voice: str, speed: float) -> Synthesis:
        pipeline = self._pipeline(lang_code(voice))
        results = self._offline_first(lambda: list(pipeline(text, voice=voice, speed=speed)))
        chunks: list[np.ndarray] = []
        words: list[WordTiming] = []
        offset = 0.0
        for result in results:
            if result.audio is None:
                continue
            audio = np.asarray(result.audio, dtype=np.float32).reshape(-1)
            for token in result.tokens or []:
                if token.start_ts is None or token.end_ts is None or not token.text.strip():
                    continue
                words.append(
                    WordTiming(
                        text=token.text,
                        start=round(offset + float(token.start_ts), 3),
                        end=round(offset + float(token.end_ts), 3),
                        phonemes=token.phonemes or "",
                    )
                )
            chunks.append(audio)
            offset += len(audio) / SAMPLE_RATE
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        return Synthesis(audio=audio, sample_rate=SAMPLE_RATE, words=words)

    @staticmethod
    def _offline_first(load: Callable[[], Any]) -> Any:
        """Use the cache without network; download only if something is missing (first run)."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                with _hf_offline(True):
                    return load()
            except Exception as exc:  # not cached yet
                log.info("Kokoro files not cached (%s); downloading once from Hugging Face", exc)
                return load()
