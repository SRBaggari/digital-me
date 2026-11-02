"""P4 — speech-to-text: voice activity detection and transcription."""

from .base import STTError, Transcriber, Transcript
from .preferences import ListeningPreferences, ListeningUpdate
from .vad import FRAME, SAMPLE_RATE, SileroVAD, SpeechDetector, SpeechEnded, SpeechStarted
from .whisper import WhisperTranscriber

__all__ = [
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
]
