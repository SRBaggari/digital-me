"""Telugu speech recognition model.

OpenAI Whisper itself cannot transcribe Telugu usefully (measured: it produced Tamil/Urdu/Hindi
script or English nonsense, even the 1.5 GB "medium" model). The models fine-tuned on Telugu
speech by IIT Madras SPRING Lab (vasista22/whisper-telugu-*, Apache-2.0) work well. They are
published for PyTorch, so on first use they are converted once to the fast CTranslate2 format
used by faster-whisper and kept in <repo>/models/ (git-ignored).
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from ..config.instance import REPO_ROOT

log = logging.getLogger(__name__)

MODELS_DIR = REPO_ROOT / "models"
SOURCE = "vasista22/whisper-telugu-{size}"


def model_dir(size: str, root: Path = MODELS_DIR) -> Path:
    return root / f"whisper-telugu-{size}-ct2"


def is_ready(path: Path) -> bool:
    return (path / "model.bin").is_file() and (path / "tokenizer.json").is_file()


def ensure_model(size: str = "base", root: Path = MODELS_DIR) -> Path:
    """Return the converted model directory, downloading and converting it the first time."""
    path = model_dir(size, root)
    if is_ready(path):
        return path
    log.info("Preparing the Telugu speech model (%s); first use only", SOURCE.format(size=size))
    from ctranslate2.converters import TransformersConverter
    from transformers import WhisperTokenizerFast

    repo = SOURCE.format(size=size)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
        staging = Path(tmp) / "model"
        TransformersConverter(
            repo, copy_files=["tokenizer_config.json", "preprocessor_config.json"]
        ).convert(str(staging), quantization="int8")
        # faster-whisper needs tokenizer.json, which these repositories don't ship
        WhisperTokenizerFast.from_pretrained(repo).save_pretrained(str(Path(tmp) / "tok"))
        shutil.copy(Path(tmp) / "tok" / "tokenizer.json", staging / "tokenizer.json")
        if path.exists():
            shutil.rmtree(path)
        shutil.move(str(staging), path)
    return path
