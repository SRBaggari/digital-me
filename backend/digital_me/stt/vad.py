"""Voice activity detection: decides when the user starts and stops talking.

SpeechDetector is a pure state machine over per-frame speech probabilities, so it can be tested
without audio. SileroVAD supplies those probabilities from the real model.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16_000
FRAME = 512  # samples per decision (32 ms); the size Silero VAD expects at 16 kHz
FRAME_MS = FRAME * 1000 // SAMPLE_RATE


@dataclass(frozen=True)
class SpeechStarted:
    pass


@dataclass(frozen=True)
class SpeechEnded:
    audio: np.ndarray  # float32 mono 16 kHz, including a little audio from before speech began

    @property
    def duration(self) -> float:
        return len(self.audio) / SAMPLE_RATE


SpeechEvent = SpeechStarted | SpeechEnded


class SpeechDetector:
    def __init__(
        self,
        probability: Callable[[np.ndarray], float],
        *,
        threshold: float = 0.5,
        playback_threshold: float = 0.85,
        min_speech_ms: int = 250,
        playback_min_speech_ms: int = 450,
        min_silence_ms: int = 700,
        pre_roll_ms: int = 300,
        max_utterance_s: float = 30.0,
    ):
        self._probability = probability
        self.threshold = threshold
        self.playback_threshold = playback_threshold
        self.min_speech_ms = min_speech_ms
        self.playback_min_speech_ms = playback_min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.max_frames = int(max_utterance_s * 1000 / FRAME_MS)
        # While Digital Me's own voice is playing, demand clearer and longer speech so that
        # leftover echo from the speakers is not mistaken for the user.
        self.playback = False
        self._pending = np.zeros(0, dtype=np.float32)
        self._pre_roll: deque[np.ndarray] = deque(maxlen=max(1, pre_roll_ms // FRAME_MS))
        self._candidate: list[np.ndarray] = []
        self._utterance: list[np.ndarray] = []
        self._silence_frames = 0
        self.speaking = False

    def feed(self, samples: np.ndarray) -> list[SpeechEvent]:
        self._pending = np.concatenate([self._pending, np.asarray(samples, dtype=np.float32)])
        events: list[SpeechEvent] = []
        while len(self._pending) >= FRAME:
            frame, self._pending = self._pending[:FRAME], self._pending[FRAME:]
            event = self._step(frame, float(self._probability(frame)))
            if event is not None:
                events.append(event)
        return events

    def reset(self) -> None:
        self._pending = np.zeros(0, dtype=np.float32)
        self._pre_roll.clear()
        self._candidate = []
        self._utterance = []
        self._silence_frames = 0
        self.speaking = False

    def _step(self, frame: np.ndarray, p: float) -> SpeechEvent | None:
        start = self.playback_threshold if self.playback else self.threshold
        keep = start - 0.15  # hysteresis: easier to stay in speech than to enter it
        if not self.speaking:
            if p >= start:
                self._candidate.append(frame)
                needed = self.playback_min_speech_ms if self.playback else self.min_speech_ms
                if len(self._candidate) * FRAME_MS >= needed:
                    self.speaking = True
                    self._utterance = [*self._pre_roll, *self._candidate]
                    self._candidate, self._silence_frames = [], 0
                    self._pre_roll.clear()
                    return SpeechStarted()
            else:
                # a blip shorter than min_speech: treat as background, keep it as pre-roll
                for f in self._candidate:
                    self._pre_roll.append(f)
                self._candidate = []
                self._pre_roll.append(frame)
            return None

        self._utterance.append(frame)
        self._silence_frames = 0 if p >= keep else self._silence_frames + 1
        if self._silence_frames * FRAME_MS >= self.min_silence_ms or len(self._utterance) >= self.max_frames:
            audio = np.concatenate(self._utterance)
            self._utterance, self._silence_frames, self.speaking = [], 0, False
            return SpeechEnded(audio)
        return None


class SileroVAD:
    """Silero VAD (MIT). One instance per audio stream: the model keeps internal state."""

    def __init__(self) -> None:
        import torch
        from silero_vad import load_silero_vad  # model file ships inside the package

        self._torch = torch
        self._model = load_silero_vad()

    def __call__(self, frame: np.ndarray) -> float:
        with self._torch.no_grad():
            return float(self._model(self._torch.from_numpy(frame), SAMPLE_RATE).item())

    def reset(self) -> None:
        self._model.reset_states()
