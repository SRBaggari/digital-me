"""Incremental sentence splitting so speech can start before the whole reply is generated."""

from __future__ import annotations

import re

ABBREVIATIONS = frozenset(
    {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "approx", "fig"}
)
_TERMINATORS = ".!?…।॥"  # including the danda used in Indian scripts
_CLOSERS = "\"')]”’»"
_WORD_BEFORE = re.compile(r"([A-Za-z.]+)$")


class SentenceSplitter:
    def __init__(self) -> None:
        self._buffer = ""

    @property
    def pending(self) -> str:
        return self._buffer

    def feed(self, text: str) -> list[str]:
        self._buffer += text
        sentences: list[str] = []
        while (cut := self._find_boundary(self._buffer)) is not None:
            sentence = self._buffer[:cut].strip()
            self._buffer = self._buffer[cut:]
            if sentence:
                sentences.append(sentence)
        return sentences

    def flush(self) -> list[str]:
        rest, self._buffer = self._buffer.strip(), ""
        return [rest] if rest else []

    def _find_boundary(self, s: str) -> int | None:
        i = 0
        while i < len(s):
            char = s[i]
            if char == "\n":
                return i + 1
            if char in _TERMINATORS:
                j = i + 1
                while j < len(s) and (s[j] in _TERMINATORS or s[j] in _CLOSERS):
                    j += 1
                if j >= len(s):
                    return None  # cannot decide until the next character arrives
                if s[j].isspace() and not (char == "." and _is_abbreviation(s, i)):
                    return j
                i = j
                continue
            i += 1
        return None


def _is_abbreviation(s: str, dot_index: int) -> bool:
    match = _WORD_BEFORE.search(s[:dot_index])
    if not match:
        return False
    word = match.group(1)
    if word.lower() in ABBREVIATIONS:
        return True
    # A single capital letter is usually an initial ("J. Smith"); "I" is a pronoun.
    return len(word) == 1 and word.isupper() and word != "I"
