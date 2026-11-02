"""Shared fixtures. Test classification is derived from file location and name:

    tests/<part>/unit/test_<feature>_whitebox.py         -> whitebox
    tests/<part>/integration/test_<feature>_blackbox.py  -> blackbox + integration
"""

from __future__ import annotations

from pathlib import Path

import pytest

from digital_me.config import instance as instance_module


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        stem = item.path.stem
        if stem.endswith("_whitebox"):
            item.add_marker(pytest.mark.whitebox)
        elif stem.endswith("_blackbox"):
            item.add_marker(pytest.mark.blackbox)
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def instances_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty, private instances directory for one test."""
    home = tmp_path / "instances"
    monkeypatch.setenv(instance_module.HOME_ENV_VAR, str(home))
    return home


@pytest.fixture
def template_dir() -> Path:
    return instance_module.TEMPLATE_DIR
