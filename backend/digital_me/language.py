"""Which language a piece of text is in. Digital Me answers in the language it is spoken to.

Detection is by script, which is reliable for the supported pair: Telugu has its own
alphabet (U+0C00-U+0C7F); anything else written in Latin letters is treated as English.
"""

from __future__ import annotations

LANGUAGES: dict[str, str] = {"en": "English", "te": "Telugu"}
DEFAULT_LANGUAGE = "en"

_TELUGU = range(0x0C00, 0x0C80)


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
    return "te" if telugu >= 0.3 * (telugu + latin) else "en"


def reply_instruction(language: str) -> str:
    """Instruction appended to each turn so even small models answer in the right language."""
    if language == "te":
        # Names and English words must be in Telugu script too: the Telugu voice cannot read
        # Latin letters (an earlier version replied just "Pixel." and stayed silent).
        return (
            "The user is speaking Telugu. Reply ONLY in Telugu, in full sentences, written in "
            "Telugu script (తెలుగు లిపి). Write names and English words in Telugu letters as they "
            "sound, for example Miso -> మిసో, jazz -> జాజ్. Do not use English letters or any other "
            "script. Keep only the emotion tag in English, for example [happy]."
        )
    return "The user is speaking English. Reply in English."
