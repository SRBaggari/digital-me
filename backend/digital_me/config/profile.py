"""Identity profile of the person a Digital Me instance represents."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class ProfileError(Exception):
    """Raised when a profile file is missing or invalid."""


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    short_bio: str = Field(default="", max_length=1000)
    personality_traits: list[str] = Field(default_factory=list)
    communication_style: str = Field(default="", max_length=1000)
    interests: list[str] = Field(default_factory=list)
    background: list[str] = Field(default_factory=list)
    important_facts: list[str] = Field(default_factory=list)
    expressions: list[str] = Field(default_factory=list)

    @field_validator("name", "short_bio", "communication_style")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator(
        "personality_traits", "interests", "background", "important_facts", "expressions",
        mode="before",
    )
    @classmethod
    def _clean_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("must be a list of strings")
        cleaned = []
        for item in value:
            if not isinstance(item, (str, int, float)):
                raise ValueError("list items must be text")
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned


def load_profile(path: Path) -> Profile:
    if not path.is_file():
        raise ProfileError(f"Profile not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileError(f"Profile is not valid YAML: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"Profile must be a YAML mapping: {path}")
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        raise ProfileError(f"Invalid profile {path}:\n{exc}") from exc
