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
    # Telugu: when answering in Telugu, gemma sometimes writes the tag in Telugu too
    "సంతోషం": "happy",
    "సంతోషంగా": "happy",
    "ఆనందం": "happy",
    "ఆనందంగా": "happy",
    "నవ్వుతూ": "happy",
    "ఉత్సాహంగా": "happy",
    "తటస్థం": "neutral",
    "సాధారణం": "neutral",
    "ప్రశాంతంగా": "neutral",
    "గంభీరంగా": "serious",
    "తీవ్రంగా": "serious",
    "ఆశ్చర్యం": "surprised",
    "ఆశ్చర్యంగా": "surprised",
    "విచారం": "sad",
    "విచారంగా": "sad",
    "బాధ": "sad",
    "బాధగా": "sad",
    "సానుభూతి": "empathetic",
    "సానుభూతితో": "empathetic",
}

_TELUGU = range(0x0C00, 0x0C80)


def _is_telugu_tag(inner: str) -> bool:
    """A short bracketed Telugu phrase in a reply is a stage direction, never content."""
    text = inner.strip()
    return 0 < len(text) <= 24 and all(ord(c) in _TELUGU or c.isspace() for c in text)

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
                if _cannot_be_tag(self._buffer[1:]):
                    parts.append(TextPart("["))
                    self._buffer = self._buffer[1:]
                    continue
                break  # possibly an incomplete tag: wait for more input
            inner = self._buffer[1:end]
            if "[" in inner or _cannot_be_tag(inner):
                parts.append(TextPart("["))
                self._buffer = self._buffer[1:]
                continue
            emotion = normalize_emotion(inner)
            if emotion:
                parts.append(EmotionPart(emotion))
            elif not _is_telugu_tag(inner):  # unknown Telugu tags are dropped silently
                parts.append(TextPart(self._buffer[: end + 1]))
            self._buffer = self._buffer[end + 1:]
        return _merge(parts)

    def flush(self) -> list[Part]:
        rest, self._buffer = self._buffer, ""
        return [TextPart(rest)] if rest else []


def _cannot_be_tag(inner: str) -> bool:
    # Same rule whether or not the closing ']' has arrived, so chunking never changes results.
    return len(inner) > _MAX_TAG_LENGTH or "\n" in inner


def _merge(parts: list[Part]) -> list[Part]:
    merged: list[Part] = []
    for part in parts:
        if isinstance(part, TextPart) and merged and isinstance(merged[-1], TextPart):
            merged[-1] = TextPart(merged[-1].text + part.text)
        else:
            merged.append(part)
    return merged
