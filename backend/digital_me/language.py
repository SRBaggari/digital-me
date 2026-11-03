"""Which language a piece of text is in. Digital Me answers in the language it is spoken to.

Telugu can be written in its own script (U+0C00-U+0C7F) or romanised, in English letters
("ela unnavu?"). Telugu script is detected by its letters; romanised Telugu by common Telugu
words, since it shares the alphabet with English. Everything else is English.
"""

from __future__ import annotations

import re

from .romanised_telugu import NORMALISED_WORDS, WORDS, is_english_word, normalise

LANGUAGES: dict[str, str] = {"en": "English", "te": "Telugu"}
DEFAULT_LANGUAGE = "en"

_TELUGU = range(0x0C00, 0x0C80)
_WORD = re.compile(r"[a-z]+")

# Frequent romanised Telugu words, used to recognise romanised Telugu. Short words that are
# also English ("a", "to", "e", "na", "mi", "ga", "lo", "ki") are excluded from recognition.
_AMBIGUOUS = {"e", "na", "mi", "ga", "lo", "ki", "to", "tho", "em", "mari", "anna", "amma", "emi"}
ROMANISED_TELUGU_WORDS = frozenset(set(WORDS) - _AMBIGUOUS)
_AMBIGUOUS_NORMALISED = {normalise(word) for word in _AMBIGUOUS}


def _is_telugu_word(word: str) -> bool:
    if word in ROMANISED_TELUGU_WORDS:
        return True
    # A spelling variant ("chesthunaru") counts too, unless it is simply an English word
    # ("to" normalises like "tho") or one of the short ambiguous words.
    key = normalise(word)
    return key in NORMALISED_WORDS and key not in _AMBIGUOUS_NORMALISED and not is_english_word(word)


def is_romanised_telugu(text: str) -> bool:
    words = _WORD.findall(text.lower())
    if not words:
        return False
    hits = sum(_is_telugu_word(word) for word in words)
    # Two Telugu words, or one in a very short message ("bagunnava?"), and at least a quarter
    # of the words: avoids mistaking an English sentence with a name like "Ela" for Telugu.
    return (hits >= 2 or (hits == 1 and len(words) <= 2)) and hits / len(words) >= 0.25


def detect_language(text: str) -> str | None:
    """'te' or 'en', or None when the text has no letters (e.g. only digits or emoji)."""
    telugu = latin = 0
    for char in text:
        code = ord(char)
        if code in _TELUGU:
            telugu += 1
        elif char.isascii() and char.isalpha():
            latin += 1
    if telugu == 0 and latin == 0:
        return None
    # Telugu replies often contain English names ("జాజ్ (jazz)"); a Telugu-script share of
    # 30% is a clear signal that the person is writing Telugu.
    if telugu >= 0.3 * (telugu + latin):
        return "te"
    return "te" if is_romanised_telugu(text) else "en"


def reply_instruction(language: str, romanised: bool = False) -> str:
    """Instruction appended to each turn so even small models answer in the right language."""
    if language == "te":
        # Names and English words must be in Telugu script too: the Telugu voice cannot read
        # Latin letters (an earlier version replied just "Pixel." and stayed silent).
        heard = (
            "The user wrote Telugu in English letters; it was converted to Telugu script "
            "automatically, so some words may be spelled oddly. "
            if romanised
            else "The user is speaking Telugu. "
        )
        return (
            heard + "Reply ONLY in Telugu, in full sentences, written in "
            "Telugu script (తెలుగు లిపి). Write names and English words in Telugu letters as they "
            "sound, for example Miso -> మిసో, jazz -> జాజ్. Do not use English letters or any other "
            "script. Keep only the emotion tag in English, for example [happy]; never translate it."
        )
    return (
        "The user is speaking English. Reply in English. (If the message is actually Telugu "
        "written in English letters, understand it as Telugu and reply in Telugu script.)"
    )
