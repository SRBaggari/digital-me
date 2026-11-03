"""P5 — text-to-speech."""

from .base import Synthesis, TTSEngine, TTSError, Voice, WordTiming
from .encoding import to_wav_base64, to_wav_bytes
from .kokoro_engine import KokoroEngine
from .mms_engine import MmsEngine
from .multilingual import LanguageRouter
from .preferences import VoicePreferences, VoiceUpdate

__all__ = [
    "KokoroEngine",
    "LanguageRouter",
    "MmsEngine",
    "Synthesis",
    "TTSEngine",
    "TTSError",
    "Voice",
    "VoicePreferences",
    "VoiceUpdate",
    "WordTiming",
    "to_wav_base64",
    "to_wav_bytes",
]
