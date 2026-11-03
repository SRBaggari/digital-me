"""P4 — speech-to-text: voice activity detection and transcription."""

from . import telugu_model
from .base import STTError, Transcriber, Transcript
from .bilingual import BilingualTranscriber
from .preferences import ListeningPreferences, ListeningUpdate
from .vad import FRAME, SAMPLE_RATE, SileroVAD, SpeechDetector, SpeechEnded, SpeechStarted
from .whisper import WhisperTranscriber

__all__ = [
    "BilingualTranscriber",
    "FRAME",
    "ListeningPreferences",
    "ListeningUpdate",
    "SAMPLE_RATE",
    "STTError",
    "SileroVAD",
    "SpeechDetector",
    "SpeechEnded",
    "SpeechStarted",
    "Transcriber",
    "Transcript",
    "WhisperTranscriber",
    "telugu_model",
]
