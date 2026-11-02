"""Runtime settings. Local-only: every network endpoint must be a loopback address."""

from __future__ import annotations

import ipaddress
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SettingsError(Exception):
    """Raised when a settings file is invalid."""


def is_loopback_host(host: str) -> bool:
    host = host.strip().strip("[]").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class LLMSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = "http://127.0.0.1:11434"
    model: str = Field(default="llama3.2:3b", min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    context_turns: int = Field(default=12, ge=1, le=100)
    num_ctx: int = Field(default=4096, ge=512, le=131072)

    @field_validator("base_url")
    @classmethod
    def _local_only(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"base_url must be an http(s) URL, got {value!r}")
        if not is_loopback_host(parsed.hostname):
            raise ValueError(
                f"base_url must point to this computer (localhost/127.0.0.1); got {parsed.hostname!r}"
            )
        return value.rstrip("/")


class ServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1024, le=65535)

    @field_validator("host")
    @classmethod
    def _loopback_only(cls, value: str) -> str:
        if not is_loopback_host(value):
            raise ValueError(f"server host must be a loopback address, got {value!r}")
        return value


class VoiceSettings(BaseModel):
    """Default voice; the UI can override these per instance."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    engine: Literal["kokoro"] = "kokoro"
    voice: str = Field(default="af_heart", min_length=1, max_length=64)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)


def load_settings(path: Path) -> Settings:
    """Load settings; a missing file means all defaults."""
    if not path.is_file():
        return Settings()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SettingsError(f"Settings are not valid YAML: {path}: {exc}") from exc
    if data is None:
        return Settings()
    if not isinstance(data, dict):
        raise SettingsError(f"Settings must be a YAML mapping: {path}")
    try:
        return Settings.model_validate(data)
    except ValidationError as exc:
        raise SettingsError(f"Invalid settings {path}:\n{exc}") from exc
