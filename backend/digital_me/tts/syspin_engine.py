"""Female Telugu voice: SYSPIN's VITS model (IISc SPIRE lab, 30 h female speaker, CC-BY-4.0).

Distributed as a self-contained TorchScript model. Its repository also ships a Python tokenizer
file; that downloaded code is not executed. The few lines it does are reimplemented here
(Coqui VITS character vocabulary, light text cleaning, blank tokens between characters).
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from typing import Any

import numpy as np

from .base import Synthesis, TTSError, Voice

log = logging.getLogger(__name__)

REPO_ID = "SYSPIN/tts_vits_coquiai_TeluguFemale"
MODEL_FILE = "te_female_vits_30hrs.pt"
CHARS_FILE = "chars.txt"
SAMPLE_RATE = 22_050
VOICE = Voice("te_female", "Telugu (female)", "Telugu", "female")

PAD, BLANK = "<PAD>", "<BLNK>"
PUNCTUATIONS = "!¡'(),-.:;¿? "


def fetch(filename: str) -> str:
    """Local path of a model file: from the cache with no network request when present."""
    from huggingface_hub import hf_hub_download

    try:
        return hf_hub_download(repo_id=REPO_ID, filename=filename, local_files_only=True)
    except Exception:
        log.info("Downloading %s from Hugging Face (first use only)", filename)
        return hf_hub_download(repo_id=REPO_ID, filename=filename)


class Tokenizer:
    """Text -> ids exactly as the model was trained (Coqui VitsCharacters + add_blank)."""

    def __init__(self, letters: str):
        vocab = [PAD, *PUNCTUATIONS, *letters, BLANK]
        self._ids = {char: index for index, char in enumerate(vocab)}
        self.blank_id = self._ids[BLANK]

    @staticmethod
    def clean(text: str) -> str:
        text = text.lower().replace(";", ",").replace("-", " ").replace(":", ",")
        text = re.sub(r"[<>()\[\]\"]+", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def encode(self, text: str) -> list[int]:
        ids = [self._ids[char] for char in self.clean(text) if char in self._ids]
        if not ids:
            return []
        out = [self.blank_id] * (len(ids) * 2 + 1)
        out[1::2] = ids
        return out


def _default_loader() -> tuple[Any, Tokenizer]:
    import torch

    with open(fetch(CHARS_FILE), encoding="utf-8") as handle:
        letters = handle.read().strip("\n")
    model = torch.jit.load(fetch(MODEL_FILE), map_location="cpu").eval()
    return model, Tokenizer(letters)


class SyspinEngine:
    name = "syspin"

    def __init__(self, loader: Callable[[], tuple[Any, Tokenizer]] = _default_loader):
        self._loader = loader
        self._model: Any = None
        self._tokenizer: Tokenizer | None = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def voices(self) -> list[Voice]:
        return [VOICE]

    def warm_up(self, voice: str = VOICE.id) -> None:
        self.synthesize("నమస్కారం.", VOICE.id, 1.0)

    def synthesize(self, text: str, voice: str, speed: float) -> Synthesis:
        with self._lock:
            try:
                import torch

                if self._model is None:
                    self._model, self._tokenizer = self._loader()
                ids = self._tokenizer.encode(text)
                if not ids:
                    return Synthesis(np.zeros(0, dtype=np.float32), SAMPLE_RATE)
                with torch.no_grad():
                    waveform = self._model(torch.tensor([ids], dtype=torch.long))
            except Exception as exc:
                log.exception("Telugu synthesis failed")
                raise TTSError(f"Telugu speech synthesis failed: {exc}") from exc
        audio = np.asarray(waveform, dtype=np.float32).reshape(-1)
        return Synthesis(audio=_change_speed(audio, speed), sample_rate=SAMPLE_RATE)


def _change_speed(audio: np.ndarray, speed: float) -> np.ndarray:
    """The model has a fixed speaking rate; apply the user's speed by resampling the timeline.
    Kept within a small range so the pitch change stays natural."""
    speed = min(max(speed, 0.85), 1.15)
    if abs(speed - 1.0) < 0.01 or len(audio) == 0:
        return audio
    positions = np.arange(0, len(audio), speed)
    return np.interp(positions, np.arange(len(audio)), audio).astype(np.float32)
