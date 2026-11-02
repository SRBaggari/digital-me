"""Spec: everything must stay on this computer; numeric settings have documented ranges."""

import pytest
from pydantic import ValidationError

from digital_me.config import LLMSettings, ServerSettings, Settings, load_settings


def test_missing_file_gives_safe_defaults(tmp_path):
    settings = load_settings(tmp_path / "absent.yaml")
    assert settings.server.host == "127.0.0.1"
    assert settings.llm.base_url.startswith("http://127.0.0.1")


def test_template_settings_are_valid(template_dir):
    assert load_settings(template_dir / "settings.yaml") == Settings()


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.0.5", "my-pc.local", "::"])
def test_server_refuses_non_loopback(host):
    with pytest.raises(ValidationError):
        ServerSettings(host=host)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "http://10.0.0.2:11434",
        "http://ollama.example.com",
        "ftp://127.0.0.1",
    ],
)
def test_llm_refuses_remote_endpoints(url):
    with pytest.raises(ValidationError):
        LLMSettings(base_url=url)


@pytest.mark.parametrize("url", ["http://localhost:11434", "http://127.0.0.1:9999", "http://[::1]:1"])
def test_llm_accepts_local_endpoints(url):
    assert LLMSettings(base_url=url)


@pytest.mark.parametrize(
    "field, value, ok",
    [
        ("temperature", 0.0, True),
        ("temperature", 2.0, True),
        ("temperature", -0.01, False),
        ("temperature", 2.01, False),
        ("context_turns", 1, True),
        ("context_turns", 100, True),
        ("context_turns", 0, False),
        ("context_turns", 101, False),
    ],
)
def test_llm_ranges(field, value, ok):
    if ok:
        assert getattr(LLMSettings(**{field: value}), field) == value
    else:
        with pytest.raises(ValidationError):
            LLMSettings(**{field: value})


@pytest.mark.parametrize("port, ok", [(1023, False), (1024, True), (65535, True), (65536, False)])
def test_port_boundaries(port, ok):
    if ok:
        assert ServerSettings(port=port).port == port
    else:
        with pytest.raises(ValidationError):
            ServerSettings(port=port)


def test_unknown_keys_rejected():
    with pytest.raises(ValidationError):
        Settings.model_validate({"cloud": {"api_key": "x"}})
