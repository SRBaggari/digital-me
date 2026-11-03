"""Turns the browser's microphone stream into transcribed utterances."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..config import ListeningSettings
from ..preferences import Preferences
from ..stt import SpeechDetector, SpeechEnded, SpeechStarted, STTError, Transcriber

log = logging.getLogger(__name__)
Send = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class Hearing:
    """Everything a session needs to listen: the transcriber, a VAD factory and preferences."""

    transcriber: Transcriber
    vad_factory: Callable[[], Callable[[np.ndarray], float]]
    preferences: Preferences[ListeningSettings]


def pcm16_to_float(data: bytes) -> np.ndarray:
    usable = len(data) - (len(data) % 2)
    return np.frombuffer(data[:usable], dtype="<i2").astype(np.float32) / 32768.0


class Listener:
    """One per open microphone. Audio in; speech start/end and transcripts out (via callbacks)."""

    def __init__(
        self,
        detector: SpeechDetector,
        transcriber: Transcriber,
        *,
        on_speech_start: Callable[[], Awaitable[None]],
        on_transcript: Callable[[str, str | None], Awaitable[None]],
        send: Send,
        on_speech_end: Callable[[], Awaitable[None]] | None = None,
    ):
        self._detector = detector
        self._transcriber = transcriber
        self._on_speech_start = on_speech_start
        self._on_transcript = on_transcript
        self._on_speech_end = on_speech_end
        self._send = send
        self._jobs: asyncio.Queue[np.ndarray | None] = asyncio.Queue()
        self._worker = asyncio.create_task(self._transcribe_in_order())

    @property
    def playback(self) -> bool:
        return self._detector.playback

    @playback.setter
    def playback(self, playing: bool) -> None:
        self._detector.playback = playing

    async def feed(self, data: bytes) -> None:
        for event in self._detector.feed(pcm16_to_float(data)):
            if isinstance(event, SpeechStarted):
                await self._send({"type": "user_speaking", "speaking": True})
                await self._on_speech_start()
            elif isinstance(event, SpeechEnded):
                # Even one-word answers ("yes") are transcribed; clicks never get this far
                # (speech must last 250 ms to start) and Whisper drops noise it is unsure of.
                await self._send({"type": "user_speaking", "speaking": False})
                await self._send({"type": "transcribing"})
                self._jobs.put_nowait(event.audio)
                if self._on_speech_end is not None:
                    await self._on_speech_end()

    async def close(self) -> None:
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass

    async def _transcribe_in_order(self) -> None:
        while (audio := await self._jobs.get()) is not None:
            try:
                transcript = await asyncio.to_thread(self._transcriber.transcribe, audio)
            except STTError as exc:
                await self._send({"type": "error", "code": "stt_error", "detail": str(exc)})
                await self._send({"type": "transcript", "text": ""})
                continue
            await self._send(
                {"type": "transcript", "text": transcript.text, "language": transcript.language}
            )
            if transcript.text:
                await self._on_transcript(transcript.text, transcript.language)
