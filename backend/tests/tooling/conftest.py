import importlib.util

import pytest

from digital_me.config.instance import REPO_ROOT


@pytest.fixture(scope="session")
def guard():
    spec = importlib.util.spec_from_file_location("check_private", REPO_ROOT / "scripts" / "check_private.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
