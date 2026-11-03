"""Incremental sentence splitting so speech can start before the whole reply is generated."""

from __future__ import annotations

import re

ABBREVIATIONS = frozenset(
    {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "approx", "fig"}
)
_TERMINATORS = ".!?…।॥"  # including the danda used in Indian scripts
_CLOSERS = "\"')]”’»"
_WORD_BEFORE = re.compile(r"([A-Za-z.]+)$")
_CLAUSE_END = re.compile(r"[,;:—–](?=\s)")


class SentenceSplitter:
    """Emits complete sentences as text streams in.

    With `first_clause_words`, the very first piece is emitted as soon as a clause of at least
    that many words is complete ("Usually, I head out climbing," ...), so the voice can start
    while the model is still writing the rest of the first sentence.
    """

    def __init__(self, first_clause_words: int | None = None) -> None:
        self._buffer = ""
        self._first_clause_words = first_clause_words
        self._emitted = False

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
                self._emitted = True
        return sentences

    def flush(self) -> list[str]:
        rest, self._buffer = self._buffer.strip(), ""
        return [rest] if rest else []

    def _find_boundary(self, s: str) -> int | None:
        sentence_end = self._sentence_boundary(s)
        if self._emitted or self._first_clause_words is None:
            return sentence_end
        clause_end = self._clause_boundary(s)
        if clause_end is None:
            return sentence_end
        return clause_end if sentence_end is None else min(clause_end, sentence_end)

    def _clause_boundary(self, s: str) -> int | None:
        for match in _CLAUSE_END.finditer(s):
            if len(s[: match.end()].split()) >= self._first_clause_words:
                return match.end()
        return None

    def _sentence_boundary(self, s: str) -> int | None:
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
