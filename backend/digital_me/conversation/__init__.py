"""P2 — conversation engine."""

from .emotion import DEFAULT_EMOTION, EMOTIONS, EmotionTagParser, normalize_emotion
from .engine import (
    MAX_INPUT_CHARS,
    ConversationEngine,
    EmotionChanged,
    SentenceReady,
    TextDelta,
    TurnCompleted,
    TurnEvent,
    TurnStarted,
)
from .history import Conversation, ConversationNotFoundError, ConversationStore, Message
from .prompt import build_chat_messages, build_system_prompt
from .sentences import SentenceSplitter

__all__ = [
    "DEFAULT_EMOTION",
    "EMOTIONS",
    "MAX_INPUT_CHARS",
    "Conversation",
    "ConversationEngine",
    "ConversationNotFoundError",
    "ConversationStore",
    "EmotionChanged",
    "EmotionTagParser",
    "Message",
    "SentenceReady",
    "SentenceSplitter",
    "TextDelta",
    "TurnCompleted",
    "TurnEvent",
    "TurnStarted",
    "build_chat_messages",
    "build_system_prompt",
    "normalize_emotion",
]
