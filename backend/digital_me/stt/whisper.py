"""Speech-to-text with faster-whisper (MIT), on the CPU so the GPU stays free for the LLM."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import numpy as np

from .base import STTError, Transcript

log = logging.getLogger(__name__)

# Whisper sometimes "hears" words in noise; segments it is unsure contain speech are dropped.
NO_SPEECH_LIMIT = 0.6
LOGPROB_LIMIT = -1.0


def _default_model_factory(name: str) -> Any:
    from faster_whisper import WhisperModel  # heavy import, deferred

    try:  # cached copy, no network request
        return WhisperModel(name, device="cpu", compute_type="int8", local_files_only=True)
    except Exception:
        log.info("Downloading Whisper model %s from Hugging Face (first use only)", name)
        return WhisperModel(name, device="cpu", compute_type="int8")


class WhisperTranscriber:
    name = "faster-whisper"

    def __init__(
        self,
        model: str = "base.en",
        language: str = "en",
        model_factory: Callable[[str], Any] = _default_model_factory,
    ):
        self.model_name = model
        self.language = language
        self._factory = model_factory
        self._model: Any = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def warm_up(self) -> None:
        self.transcribe(np.zeros(16_000, dtype=np.float32))

    def transcribe(self, audio: np.ndarray) -> Transcript:
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        duration = len(audio) / 16_000
        with self._lock:
            try:
                if self._model is None:
                    self._model = self._factory(self.model_name)
                segments, _info = self._model.transcribe(
                    audio,
                    language=self.language,
                    beam_size=1,
                    vad_filter=False,  # the stream was already cut at speech boundaries
                    condition_on_previous_text=False,
                    without_timestamps=True,
                )
                kept = [
                    s
                    for s in segments
                    if not (s.no_speech_prob > NO_SPEECH_LIMIT and s.avg_logprob < LOGPROB_LIMIT)
                ]
            except Exception as exc:
                log.exception("Transcription failed")
                raise STTError(f"Could not transcribe speech: {exc}") from exc
        return Transcript(
            text=" ".join(t for t in (s.text.strip() for s in kept) if t).strip(),
            duration=duration,
            language=self.language,
            confidence=float(np.mean([s.avg_logprob for s in kept])) if kept else None,
        )
