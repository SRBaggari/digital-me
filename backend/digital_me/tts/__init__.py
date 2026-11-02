"""P5 — text-to-speech."""

from .base import Synthesis, TTSEngine, TTSError, Voice, WordTiming
from .encoding import to_wav_base64, to_wav_bytes
from .kokoro_engine import KokoroEngine
from .preferences import VoicePreferences, VoiceUpdate

__all__ = [
    "KokoroEngine",
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
