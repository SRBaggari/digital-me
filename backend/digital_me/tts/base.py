"""Interface every text-to-speech engine implements (built-in voices now, cloned voices later)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


class TTSError(Exception):
    """Speech could not be produced."""


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    accent: str
    gender: str


@dataclass(frozen=True)
class WordTiming:
    """When a word is spoken, in seconds from the start of its clip. Used for lip sync."""

    text: str
    start: float
    end: float
    phonemes: str = ""


@dataclass
class Synthesis:
    audio: np.ndarray  # mono float32 in [-1, 1]
    sample_rate: int
    words: list[WordTiming] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return len(self.audio) / self.sample_rate if self.sample_rate else 0.0


class TTSEngine(Protocol):
    name: str

    @property
    def ready(self) -> bool: ...

    def voices(self) -> list[Voice]: ...

    def warm_up(self) -> None:
        """Load models so the first reply is not slow. Blocking; call from a thread."""
        ...

    def synthesize(self, text: str, voice: str, speed: float) -> Synthesis:
        """Blocking; call from a thread. Raises TTSError."""
        ...
