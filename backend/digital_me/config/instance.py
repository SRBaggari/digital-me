"""Instance resolution: one directory per Digital Me, never shared."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")

# backend/digital_me/config/instance.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = REPO_ROOT / "instance-template"
HOME_ENV_VAR = "DIGITAL_ME_HOME"


class InstanceError(Exception):
    """Raised for invalid, missing or duplicate instances."""


def validate_name(name: str) -> str:
    """Return the name if it is a safe directory name, else raise InstanceError."""
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise InstanceError(
            f"Invalid instance name {name!r}: use 1-32 lowercase letters, digits, '-' or '_', "
            "starting with a letter or digit."
        )
    return name


def instances_root() -> Path:
    """Directory holding all instances (overridable for tests via DIGITAL_ME_HOME)."""
    override = os.environ.get(HOME_ENV_VAR)
    return Path(override).resolve() if override else REPO_ROOT / "instances"


@dataclass(frozen=True)
class Instance:
    name: str
    root: Path

    @property
    def profile_path(self) -> Path:
        return self.root / "profile.yaml"

    @property
    def settings_path(self) -> Path:
        return self.root / "settings.yaml"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "digital_me.sqlite3"

    @property
    def avatar_dir(self) -> Path:
        return self.root / "avatar"

    @property
    def voice_dir(self) -> Path:
        return self.root / "voice"


def resolve(name: str, root: Path | None = None) -> Instance:
    """Return an existing instance, raising InstanceError if it does not exist."""
    validate_name(name)
    base = (root or instances_root()).resolve()
    path = (base / name).resolve()
    if path.parent != base:  # defence in depth; the name pattern already forbids traversal
        raise InstanceError(f"Instance path escapes the instances directory: {path}")
    if not (path / "profile.yaml").is_file():
        raise InstanceError(
            f"Instance {name!r} not found at {path}. Create it with: digital-me init {name}"
        )
    return Instance(name=name, root=path)


def create(name: str, root: Path | None = None, template: Path | None = None) -> Instance:
    """Create a new instance directory from the template."""
    validate_name(name)
    base = (root or instances_root()).resolve()
    path = base / name
    if path.exists():
        raise InstanceError(f"Instance {name!r} already exists at {path}")
    source = template or TEMPLATE_DIR
    if not source.is_dir():
        raise InstanceError(f"Instance template not found at {source}")
    base.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, path)
    instance = Instance(name=name, root=path.resolve())
    for directory in (instance.data_dir, instance.avatar_dir, instance.voice_dir):
        directory.mkdir(exist_ok=True)
    return instance


def list_instances(root: Path | None = None) -> list[str]:
    base = root or instances_root()
    if not base.is_dir():
        return []
    return sorted(
        p.name
        for p in base.iterdir()
        if p.is_dir() and NAME_PATTERN.fullmatch(p.name) and (p / "profile.yaml").is_file()
    )
