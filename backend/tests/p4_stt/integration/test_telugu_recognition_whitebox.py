"""Real models: the converted Telugu model on disk and offline loading."""

import json

import pytest

from digital_me.stt import telugu_model

pytestmark = pytest.mark.live


def test_converted_model_is_complete_and_int8():
    try:
        path = telugu_model.ensure_model("base")
    except Exception as exc:
        pytest.skip(f"Telugu model not available: {exc}")
    assert telugu_model.is_ready(path)
    assert (path / "preprocessor_config.json").is_file()
    assert (path / "model.bin").stat().st_size < 120_000_000  # int8: ~76 MB instead of ~290 MB
    tokenizer = json.loads((path / "tokenizer.json").read_text(encoding="utf-8"))
    assert any(token["content"] == "<|te|>" for token in tokenizer["added_tokens"])


def test_second_call_reuses_converted_model(monkeypatch):
    path = telugu_model.ensure_model("base")
    monkeypatch.setattr("ctranslate2.converters.TransformersConverter", None)  # must not convert again
    assert telugu_model.ensure_model("base") == path


def test_models_directory_is_git_ignored():
    gitignore = (telugu_model.MODELS_DIR.parent / ".gitignore").read_text(encoding="utf-8")
    assert "models/" in gitignore.splitlines()
