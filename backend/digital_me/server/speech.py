"""Turns streamed sentences into audio, one sentence at a time, while the reply is still generating."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ..config import VoiceSettings
from ..tts import TTSEngine, TTSError, VoicePreferences, to_wav_base64

log = logging.getLogger(__name__)
Send = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class Speech:
    """Everything a session needs to speak: the engine and the instance's voice preferences."""

    engine: TTSEngine
    preferences: VoicePreferences


class SentenceSpeaker:
    """Consumes sentences in order and sends one `audio` event per sentence, then `speech_end`."""

    def __init__(self, engine: TTSEngine, voice: VoiceSettings, send: Send):
        self._engine = engine
        self._voice = voice
        self._send = send
        self._queue: asyncio.Queue[tuple[int, str, str] | None] = asyncio.Queue()
        self._task = asyncio.create_task(self._run())
        self.failed = False

    def say(self, index: int, text: str, emotion: str) -> None:
        self._queue.put_nowait((index, text, emotion))

    async def finish(self) -> None:
        """Wait until every queued sentence has been synthesised and sent."""
        self._queue.put_nowait(None)
        await self._task

    async def cancel(self) -> None:
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _run(self) -> None:
        while (item := await self._queue.get()) is not None:
            if self.failed:
                continue  # keep draining so finish() returns
            index, text, emotion = item
            try:
                synthesis = await asyncio.to_thread(
                    self._engine.synthesize, text, self._voice.voice, self._voice.speed
                )
            except TTSError as exc:
                self.failed = True
                await self._send({"type": "error", "code": "tts_error", "detail": str(exc)})
                continue
            if synthesis.duration == 0:
                continue
            await self._send(
                {
                    "type": "audio",
                    "index": index,
                    "text": text,
                    "emotion": emotion,
                    "sample_rate": synthesis.sample_rate,
                    "duration": round(synthesis.duration, 3),
                    "format": "wav",
                    "data": to_wav_base64(synthesis.audio, synthesis.sample_rate),
                    "words": [
                        {"text": w.text, "start": w.start, "end": w.end, "phonemes": w.phonemes}
                        for w in synthesis.words
                    ],
                }
            )
        await self._send({"type": "speech_end"})
