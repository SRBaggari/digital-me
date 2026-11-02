import pytest

from digital_me.config.settings import (
    LLMSettings,
    SettingsError,
    is_loopback_host,
    load_settings,
)


@pytest.mark.parametrize(
    "host, expected",
    [
        ("localhost", True),
        ("LOCALHOST", True),
        ("127.0.0.1", True),
        ("127.5.5.5", True),
        ("::1", True),
        ("[::1]", True),
        ("0.0.0.0", False),
        ("192.168.1.10", False),
        ("example.com", False),
        ("localhost.evil.com", False),
        ("", False),
    ],
)
def test_is_loopback_host(host, expected):
    assert is_loopback_host(host) is expected


def test_base_url_trailing_slash_removed():
    assert LLMSettings(base_url="http://localhost:11434/").base_url == "http://localhost:11434"


def test_base_url_without_scheme_rejected():
    with pytest.raises(ValueError, match="http"):
        LLMSettings(base_url="localhost:11434")


def test_empty_file_gives_defaults(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text("", encoding="utf-8")
    assert load_settings(path).llm.model == "llama3.2:3b"


def test_non_mapping_rejected(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text("- a\n", encoding="utf-8")
    with pytest.raises(SettingsError, match="mapping"):
        load_settings(path)


def test_bad_yaml_rejected(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text("llm: {", encoding="utf-8")
    with pytest.raises(SettingsError, match="YAML"):
        load_settings(path)


def test_validation_error_wrapped(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text("server:\n  port: 80\n", encoding="utf-8")
    with pytest.raises(SettingsError, match="Invalid settings"):
        load_settings(path)
