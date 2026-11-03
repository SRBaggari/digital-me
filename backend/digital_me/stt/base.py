"""Interface every speech-to-text engine implements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


class STTError(Exception):
    """Speech could not be transcribed."""


@dataclass(frozen=True)
class Transcript:
    text: str
    duration: float  # seconds of audio
    language: str | None = None  # "en" / "te" when the transcriber knows it


class Transcriber(Protocol):
    name: str

    @property
    def ready(self) -> bool: ...

    def warm_up(self) -> None:
        """Load the model. Blocking; call from a thread."""
        ...

    def transcribe(self, audio: np.ndarray) -> Transcript:
        """Float32 mono 16 kHz audio -> text. Blocking; call from a thread. Raises STTError."""
        ...
