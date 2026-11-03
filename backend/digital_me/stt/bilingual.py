"""Understands English and Telugu: identify the language, then use the best model for it.

Measured on English and Telugu clips, Whisper's language detector names English as its top
guess for English speech (81-99% sure), but for Telugu speech it often guesses Hindi, Tamil,
or even Japanese or Korean rather than Telugu. Comparing only "en" against "te" therefore sent
some Telugu speech to the English model, which produced nonsense ("E.M. Chest to Naru" for
"ఏం చేస్తున్నారు"). So: English only when English is the top guess; otherwise the other
supported language. As a safety net, a hesitant English detection whose English transcript
also has low confidence is transcribed again in the other language.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import numpy as np

from .base import STTError, Transcript
from .whisper import WhisperTranscriber, _default_model_factory

log = logging.getLogger(__name__)

ENGLISH = "en"
SURE_ENGLISH = 0.6  # detector probability above which English is trusted outright
LOW_CONFIDENCE = -0.6  # English transcripts below this are probably another language


def _default_detector_factory() -> Any:
    # Multilingual Whisper is poor at *transcribing* Telugu but tells English from non-English
    # reliably; "tiny" does that as well as "base" in half the time (~0.33 s).
    return _default_model_factory("tiny")


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

    def _other_language(self) -> str:
        return next(code for code in self._transcribers if code != ENGLISH)

    def detect(self, audio: np.ndarray) -> str:
        return self._detect(audio)[0]

    def _detect(self, audio: np.ndarray) -> tuple[str, float]:
        """(language, probability of English)."""
        if len(self._transcribers) == 1:
            return next(iter(self._transcribers)), 1.0
        with self._lock:
            try:
                if self._detector is None:
                    self._detector = self._detector_factory()
                _language, _probability, all_probs = self._detector.detect_language(audio)
            except Exception as exc:
                log.exception("Language detection failed")
                raise STTError(f"Could not tell which language was spoken: {exc}") from exc
        scores = dict(all_probs)
        english = scores.get(ENGLISH, 0.0)
        if ENGLISH not in self._transcribers:
            return max(self._transcribers, key=lambda code: scores.get(code, 0.0)), english
        top = max(scores, key=scores.get) if scores else ENGLISH
        return (ENGLISH if top == ENGLISH else self._other_language()), english

    def transcribe(self, audio: np.ndarray) -> Transcript:
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        language, english_probability = self._detect(audio)
        result = replace(self._transcribers[language].transcribe(audio), language=language)
        hesitant = english_probability < SURE_ENGLISH
        unsure = result.confidence is not None and result.confidence < LOW_CONFIDENCE
        if language == ENGLISH and hesitant and unsure and len(self._transcribers) > 1:
            other = self._other_language()
            log.info("Unsure English (%.2f, %.2f); trying %s", english_probability, result.confidence, other)
            result = replace(self._transcribers[other].transcribe(audio), language=other)
        log.info("Heard (%s, confidence %s): %s", result.language, result.confidence, result.text)
        return result
