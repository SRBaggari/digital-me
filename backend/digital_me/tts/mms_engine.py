"""Telugu speech with Meta's MMS-TTS (facebook/mms-tts-tel, CC-BY-NC-4.0: personal use only).

A small VITS model (36M parameters) that runs about 3x faster than real time on CPU.
Unlike Kokoro it gives no word timings, so lip sync falls back to audio loudness for Telugu.
"""

from __future__ import annotations

import logging
import threading
import warnings
from collections.abc import Callable
from typing import Any

import numpy as np

from .base import Synthesis, TTSError, Voice

log = logging.getLogger(__name__)

REPO_ID = "facebook/mms-tts-tel"
VOICE = Voice("te_mms", "Telugu", "Telugu", "")


def _default_loader() -> tuple[Any, Any]:
    from transformers import AutoTokenizer, VitsModel  # heavy imports, deferred

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:  # cached copy, no network request
            model = VitsModel.from_pretrained(REPO_ID, local_files_only=True)
            tokenizer = AutoTokenizer.from_pretrained(REPO_ID, local_files_only=True)
        except OSError:
            log.info("Downloading %s from Hugging Face (first use only)", REPO_ID)
            model = VitsModel.from_pretrained(REPO_ID)
            tokenizer = AutoTokenizer.from_pretrained(REPO_ID)
    return model.eval(), tokenizer


class MmsEngine:
    name = "mms"

    def __init__(self, loader: Callable[[], tuple[Any, Any]] = _default_loader):
        self._loader = loader
        self._model: Any = None
        self._tokenizer: Any = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def voices(self) -> list[Voice]:
        return [VOICE]

    def warm_up(self, voice: str = VOICE.id) -> None:
        self.synthesize("నమస్కారం.", VOICE.id, 1.0)

    def synthesize(self, text: str, voice: str, speed: float) -> Synthesis:
        text = text.strip()
        if not text:
            return Synthesis(np.zeros(0, dtype=np.float32), 16_000)
        with self._lock:
            try:
                import torch

                if self._model is None:
                    self._model, self._tokenizer = self._loader()
                inputs = self._tokenizer(text, return_tensors="pt")
                if inputs["input_ids"].shape[-1] == 0:
                    return Synthesis(np.zeros(0, dtype=np.float32), self._model.config.sampling_rate)
                self._model.speaking_rate = speed  # >1 is faster
                with torch.no_grad():
                    waveform = self._model(**inputs).waveform[0]
            except Exception as exc:
                log.exception("Telugu synthesis failed")
                raise TTSError(f"Telugu speech synthesis failed: {exc}") from exc
        audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
        return Synthesis(audio=audio, sample_rate=int(self._model.config.sampling_rate))
