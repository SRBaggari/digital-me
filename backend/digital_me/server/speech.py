"""Turns streamed sentences into audio, one sentence at a time, while the reply is still generating."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ..config import VoiceSettings
from ..tts import TTSEngine, TTSError, VoicePreferences, to_wav_base64

log = logging.getLogger(__name__)
Send = Callable[[dict[str, Any]], Awaitable[None]]

# Speech can only start once a clip is synthesised (~0.4 s per second of audio on CPU), so long
# sentences are spoken in clause-sized pieces. The very first piece of a reply is kept shortest:
# it decides how long the user waits before hearing anything.
FIRST_CHUNK_WORDS = 8
CHUNK_WORDS = 16
_CLAUSE_END = re.compile(r"[,;:—–](?=\s)")


def speakable_chunks(text: str, first: bool) -> list[str]:
    """Split a sentence at clause boundaries (commas, semicolons, dashes) into short pieces."""
    limit = FIRST_CHUNK_WORDS if first else CHUNK_WORDS
    if len(text.split()) <= limit:
        return [text]
    minimum = 3 if first else 5
    for match in _CLAUSE_END.finditer(text):
        head = text[: match.end()].strip()
        if len(head.split()) >= minimum:
            tail = text[match.end():].strip()
            if len(tail.split()) < 3:  # don't leave a tiny fragment on its own
                break
            return [head, *speakable_chunks(tail, first=False)]
    return [text]


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
        self._clips = 0
        self.failed = False

    def say(self, index: int, text: str, emotion: str) -> None:
        """Queue one sentence. `index` is the sentence number; clips are numbered separately."""
        for chunk in speakable_chunks(text, first=self._clips == 0):
            self._queue.put_nowait((self._clips, chunk, emotion))
            self._clips += 1

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
