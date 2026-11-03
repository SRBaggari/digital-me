"""One conversational turn: persona prompt + history -> streamed, emotion-tagged reply."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field

from ..config import LLMSettings, Profile
from ..language import DEFAULT_LANGUAGE, detect_language, reply_instruction
from ..llm import LLMClient, LLMError
from .emotion import DEFAULT_EMOTION, EmotionPart, EmotionTagParser, Part, TextPart
from .history import ConversationNotFoundError, ConversationStore, Message
from .prompt import build_chat_messages, build_system_prompt
from .sentences import SentenceSplitter

MAX_INPUT_CHARS = 4000
FIRST_CLAUSE_WORDS = 3
_SPACES = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True)
class TurnStarted:
    conversation_id: int
    user_message: Message


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class EmotionChanged:
    emotion: str


@dataclass(frozen=True)
class SentenceReady:
    index: int
    text: str
    emotion: str


@dataclass(frozen=True)
class TurnCompleted:
    message: Message


TurnEvent = TurnStarted | TextDelta | EmotionChanged | SentenceReady | TurnCompleted


@dataclass
class _TurnState:
    emotion: str = DEFAULT_EMOTION
    first_emotion: str | None = None
    text: list[str] = field(default_factory=list)
    sentence_count: int = 0
    # The first clause is released early so the voice can start after a few words.
    splitter: SentenceSplitter = field(
        default_factory=lambda: SentenceSplitter(first_clause_words=FIRST_CLAUSE_WORDS)
    )

    @property
    def full_text(self) -> str:
        return _SPACES.sub(" ", "".join(self.text)).strip()


class ConversationEngine:
    def __init__(
        self, profile: Profile, store: ConversationStore, llm: LLMClient, settings: LLMSettings
    ):
        self.profile = profile
        self.store = store
        self.llm = llm
        self.settings = settings
        self.system_prompt = build_system_prompt(profile)

    async def respond(
        self, conversation_id: int, user_text: str, language: str | None = None
    ) -> AsyncIterator[TurnEvent]:
        """Stream one reply in the user's language. The user message is saved first; the reply
        is saved even if the stream is cancelled or fails part-way (marked as interrupted).

        `language` comes from speech recognition; for typed text it is detected from the script.
        """
        text = user_text.strip()
        if not text:
            raise ValueError("Message is empty")
        if len(text) > MAX_INPUT_CHARS:
            raise ValueError(f"Message is longer than {MAX_INPUT_CHARS} characters")
        if not self.store.exists(conversation_id):
            raise ConversationNotFoundError(conversation_id)

        history = self.store.recent_messages(conversation_id, self.settings.context_turns)
        user_message = self.store.add_message(conversation_id, "user", text)
        yield TurnStarted(conversation_id, user_message)

        reply_language = language or detect_language(text) or DEFAULT_LANGUAGE
        messages = build_chat_messages(
            self.system_prompt, history, text, instruction=reply_instruction(reply_language)
        )
        parser = EmotionTagParser()
        state = _TurnState()
        completed = False
        try:
            async for chunk in self.llm.stream_chat(
                messages, temperature=self.settings.temperature, num_ctx=self.settings.num_ctx
            ):
                for event in self._handle(parser.feed(chunk), state):
                    yield event
            for event in self._handle(parser.flush(), state):
                yield event
            for event in self._flush_sentences(state):
                yield event
            if not state.full_text:
                raise LLMError("The model returned an empty reply")
            completed = True
        finally:
            if not completed and state.full_text:
                self.store.add_message(
                    conversation_id,
                    "assistant",
                    state.full_text,
                    emotion=state.first_emotion or DEFAULT_EMOTION,
                    interrupted=True,
                )
        reply = self.store.add_message(
            conversation_id,
            "assistant",
            state.full_text,
            emotion=state.first_emotion or DEFAULT_EMOTION,
        )
        yield TurnCompleted(reply)

    def _handle(self, parts: list[Part], state: _TurnState) -> Iterator[TurnEvent]:
        for part in parts:
            if isinstance(part, EmotionPart):
                # A tag starts a new sentence: finish the current one with the old emotion.
                yield from self._flush_sentences(state)
                is_first_tag = state.first_emotion is None
                if is_first_tag:
                    state.first_emotion = part.emotion
                if is_first_tag or part.emotion != state.emotion:
                    state.emotion = part.emotion
                    yield EmotionChanged(part.emotion)
                continue
            if not state.text and not part.text.strip():
                continue  # leading whitespace after the opening tag
            if not state.text:
                part = TextPart(part.text.lstrip())
            state.text.append(part.text)
            yield TextDelta(part.text)
            for sentence in state.splitter.feed(part.text):
                yield self._sentence(sentence, state)

    def _flush_sentences(self, state: _TurnState) -> Iterator[SentenceReady]:
        for sentence in state.splitter.flush():
            yield self._sentence(sentence, state)

    @staticmethod
    def _sentence(text: str, state: _TurnState) -> SentenceReady:
        event = SentenceReady(index=state.sentence_count, text=text, emotion=state.emotion)
        state.sentence_count += 1
        return event
