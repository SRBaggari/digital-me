"""Understands English and Telugu: identify the language, then use the best model for it."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import numpy as np

from .base import STTError, Transcript
from .whisper import WhisperTranscriber, _default_model_factory

log = logging.getLogger(__name__)


def _default_detector_factory() -> Any:
    # Multilingual Whisper is poor at *transcribing* Telugu but reliable at *recognising* it.
    return _default_model_factory("base")


class BilingualTranscriber:
    name = "faster-whisper (en+te)"

    def __init__(
        self,
        transcribers: dict[str, WhisperTranscriber],
        detector_factory: Callable[[], Any] = _default_detector_factory,
    ):
        if not transcribers:
            raise ValueError("at least one language is needed")
        self._transcribers = transcribers
        self._detector_factory = detector_factory
        self._detector: Any = None
        self._lock = threading.Lock()

    @property
    def languages(self) -> list[str]:
        return list(self._transcribers)

    @property
    def ready(self) -> bool:
        return all(t.ready for t in self._transcribers.values()) and (
            len(self._transcribers) == 1 or self._detector is not None
        )

    def warm_up(self) -> None:
        for transcriber in self._transcribers.values():
            transcriber.warm_up()
        if len(self._transcribers) > 1:
            self.detect(np.zeros(16_000, dtype=np.float32))

    def detect(self, audio: np.ndarray) -> str:
        """The most likely of the supported languages (others are ignored, not guessed)."""
        if len(self._transcribers) == 1:
            return next(iter(self._transcribers))
        with self._lock:
            try:
                if self._detector is None:
                    self._detector = self._detector_factory()
                _language, _probability, all_probs = self._detector.detect_language(audio)
            except Exception as exc:
                log.exception("Language detection failed")
                raise STTError(f"Could not tell which language was spoken: {exc}") from exc
        scores = dict(all_probs)
        return max(self._transcribers, key=lambda language: scores.get(language, 0.0))

    def transcribe(self, audio: np.ndarray) -> Transcript:
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        language = self.detect(audio)
        result = self._transcribers[language].transcribe(audio)
        return Transcript(text=result.text, duration=result.duration, language=language)
