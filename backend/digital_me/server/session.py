"""Session orchestrator: one per WebSocket connection. Runs at most one turn at a time;
a new message or an interrupt cancels the turn in progress."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import aclosing
from typing import Any

from pydantic import ValidationError

from ..conversation import (
    ConversationEngine,
    ConversationNotFoundError,
    ConversationStore,
    EmotionChanged,
    SentenceReady,
    TextDelta,
    TurnCompleted,
    TurnEvent,
    TurnStarted,
)
from ..llm import LLMError
from .protocol import (
    Interrupt,
    NewConversation,
    OpenConversation,
    UserMessage,
    client_message_adapter,
    error_event,
    message_to_dict,
)
from .speech import SentenceSpeaker, Speech

log = logging.getLogger(__name__)
Send = Callable[[dict[str, Any]], Awaitable[None]]


class Session:
    def __init__(
        self,
        engine: ConversationEngine,
        store: ConversationStore,
        send: Send,
        speech: Speech | None = None,
    ):
        self._engine = engine
        self._store = store
        self._send_raw = send
        self._speech = speech
        self._speaker: SentenceSpeaker | None = None
        self._task: asyncio.Task[None] | None = None
        self._closed = False
        self.state = "idle"
        self.conversation_id = store.latest_conversation_id() or store.create_conversation()

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        await self._send_conversation()
        await self._set_state("idle")

    async def handle(self, raw: Any) -> None:
        try:
            message = client_message_adapter.validate_python(raw)
        except ValidationError as exc:
            await self._send(error_event("bad_request", _first_error(exc)))
            return
        if isinstance(message, UserMessage):
            await self.interrupt()
            self._task = asyncio.create_task(self._run_turn(message.text))
        elif isinstance(message, Interrupt):
            await self.interrupt()
        elif isinstance(message, NewConversation):
            await self.interrupt()
            self.conversation_id = self._store.create_conversation()
            await self._send_conversation()
        elif isinstance(message, OpenConversation):
            await self.interrupt()
            if not self._store.exists(message.conversation_id):
                await self._send(error_event("not_found", "Conversation not found"))
                return
            self.conversation_id = message.conversation_id
            await self._send_conversation()

    async def interrupt(self) -> None:
        task, self._task = self._task, None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def wait_idle(self) -> None:
        """Wait for the current turn to finish (used by tests and graceful shutdown)."""
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def close(self) -> None:
        self._closed = True
        await self.interrupt()

    async def _run_turn(self, text: str) -> None:
        await self._set_state("thinking")
        self._speaker = self._start_speaker()
        try:
            # aclosing() makes sure the engine saves a partial reply even when cancellation
            # arrives while we are sending, not while the engine is awaiting the model.
            async with aclosing(self._engine.respond(self.conversation_id, text)) as events:
                async for event in events:
                    await self._forward(event)
            if self._speaker is not None:
                await self._speaker.finish()
        except asyncio.CancelledError:
            await self._send({"type": "assistant_interrupted"})
            raise
        except ValueError as exc:
            await self._send(error_event("invalid_input", str(exc)))
        except LLMError as exc:
            await self._send(error_event("llm_error", str(exc)))
        except Exception:  # never let one bad turn kill the connection
            log.exception("Unexpected error during turn")
            await self._send(error_event("internal_error", "Something went wrong. See the server log."))
        finally:
            speaker, self._speaker = self._speaker, None
            if speaker is not None:
                await speaker.cancel()  # no-op if it already finished
            await self._set_state("idle")

    def _start_speaker(self) -> SentenceSpeaker | None:
        if self._speech is None:
            return None
        voice = self._speech.preferences.get()
        if not voice.enabled:
            return None
        return SentenceSpeaker(self._speech.engine, voice, self._send)

    async def _forward(self, event: TurnEvent) -> None:
        if isinstance(event, TurnStarted):
            await self._send({"type": "user_message", "message": message_to_dict(event.user_message)})
        elif isinstance(event, EmotionChanged):
            await self._send({"type": "emotion", "emotion": event.emotion})
        elif isinstance(event, TextDelta):
            if self.state != "speaking":
                await self._set_state("speaking")
            await self._send({"type": "assistant_delta", "text": event.text})
        elif isinstance(event, SentenceReady):
            await self._send(
                {"type": "sentence", "index": event.index, "text": event.text, "emotion": event.emotion}
            )
            if self._speaker is not None:
                self._speaker.say(event.index, event.text, event.emotion)
        elif isinstance(event, TurnCompleted):
            await self._send({"type": "assistant_done", "message": message_to_dict(event.message)})

    async def _set_state(self, state: str) -> None:
        self.state = state
        await self._send({"type": "state", "state": state})

    async def _send_conversation(self) -> None:
        try:
            messages = self._store.get_messages(self.conversation_id)
        except ConversationNotFoundError:
            self.conversation_id = self._store.create_conversation()
            messages = []
        await self._send(
            {
                "type": "conversation",
                "conversation_id": self.conversation_id,
                "messages": [message_to_dict(m) for m in messages],
            }
        )

    async def _send(self, event: dict[str, Any]) -> None:
        if self._closed:
            return
        try:
            await self._send_raw(event)
        except Exception:  # connection already gone
            self._closed = True


def _first_error(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = ".".join(str(p) for p in error.get("loc", ()))
    return f"{location}: {error.get('msg', 'invalid')}" if location else error.get("msg", "invalid")
