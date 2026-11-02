"""WebSocket message schema shared with the frontend (see frontend/src/api/protocol.ts)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ..conversation import Conversation, Message

STATES = ("idle", "listening", "thinking", "speaking")


class _ClientMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserMessage(_ClientMessage):
    type: Literal["user_message"]
    text: str = Field(max_length=20_000)


class Interrupt(_ClientMessage):
    type: Literal["interrupt"]


class NewConversation(_ClientMessage):
    type: Literal["new_conversation"]


class OpenConversation(_ClientMessage):
    type: Literal["open_conversation"]
    conversation_id: int


class MicStart(_ClientMessage):
    """The user switched the microphone on; raw 16 kHz PCM frames follow as binary messages."""

    type: Literal["mic_start"]


class MicStop(_ClientMessage):
    type: Literal["mic_stop"]


class Playback(_ClientMessage):
    """Whether Digital Me's voice is audible right now (used to filter echo and for barge-in)."""

    type: Literal["playback"]
    playing: bool


ClientMessage = Annotated[
    UserMessage | Interrupt | NewConversation | OpenConversation | MicStart | MicStop | Playback,
    Field(discriminator="type"),
]
client_message_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)


def message_to_dict(message: Message) -> dict[str, Any]:
    return asdict(message)


def conversation_to_dict(conversation: Conversation) -> dict[str, Any]:
    return asdict(conversation)


def error_event(code: str, detail: str) -> dict[str, Any]:
    return {"type": "error", "code": code, "detail": detail}
