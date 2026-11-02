"""Emotion labels and a streaming parser that pulls [emotion] tags out of LLM output."""

from __future__ import annotations

from dataclasses import dataclass

EMOTIONS: tuple[str, ...] = ("neutral", "happy", "serious", "surprised", "sad", "empathetic")
DEFAULT_EMOTION = "neutral"

ALIASES: dict[str, str] = {
    "calm": "neutral",
    "joy": "happy",
    "joyful": "happy",
    "glad": "happy",
    "excited": "happy",
    "smile": "happy",
    "smiling": "happy",
    "cheerful": "happy",
    "focused": "serious",
    "thoughtful": "serious",
    "surprise": "surprised",
    "amazed": "surprised",
    "shocked": "surprised",
    "sadness": "sad",
    "sorry": "sad",
    "concerned": "empathetic",
    "caring": "empathetic",
    "sympathetic": "empathetic",
    "compassionate": "empathetic",
}

# A tag longer than this cannot be an emotion tag, so the '[' is ordinary text.
_MAX_TAG_LENGTH = 32


def normalize_emotion(raw: str) -> str | None:
    """Map '[Happy]', 'emotion: joy', ... to a known label, or None if unrecognised."""
    label = raw.strip().lower()
    for prefix in ("emotion:", "emotion=", "emotion "):
        if label.startswith(prefix):
            label = label[len(prefix):].strip()
    if label in EMOTIONS:
        return label
    return ALIASES.get(label)


@dataclass(frozen=True)
class TextPart:
    text: str


@dataclass(frozen=True)
class EmotionPart:
    emotion: str


Part = TextPart | EmotionPart


class EmotionTagParser:
    """Incrementally separates emotion tags from text, even when a tag spans chunks.

    Recognised tags become EmotionPart; any other bracketed text is passed through unchanged.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> list[Part]:
        self._buffer += chunk
        parts: list[Part] = []
        while self._buffer:
            start = self._buffer.find("[")
            if start == -1:
                parts.append(TextPart(self._buffer))
                self._buffer = ""
                break
            if start > 0:
                parts.append(TextPart(self._buffer[:start]))
                self._buffer = self._buffer[start:]
            end = self._buffer.find("]")
            if end == -1:
                if len(self._buffer) > _MAX_TAG_LENGTH or "\n" in self._buffer:
                    parts.append(TextPart("["))
                    self._buffer = self._buffer[1:]
                    continue
                break  # possibly an incomplete tag: wait for more input
            inner = self._buffer[1:end]
            if "[" in inner:
                parts.append(TextPart("["))
                self._buffer = self._buffer[1:]
                continue
            emotion = normalize_emotion(inner)
            if emotion:
                parts.append(EmotionPart(emotion))
            else:
                parts.append(TextPart(self._buffer[: end + 1]))
            self._buffer = self._buffer[end + 1:]
        return _merge(parts)

    def flush(self) -> list[Part]:
        rest, self._buffer = self._buffer, ""
        return [TextPart(rest)] if rest else []


def _merge(parts: list[Part]) -> list[Part]:
    merged: list[Part] = []
    for part in parts:
        if isinstance(part, TextPart) and merged and isinstance(merged[-1], TextPart):
            merged[-1] = TextPart(merged[-1].text + part.text)
        else:
            merged.append(part)
    return merged
