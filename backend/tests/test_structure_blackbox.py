"""Keeps the test suite organised: every part has unit and integration tests of both kinds."""

from pathlib import Path

import pytest

TESTS = Path(__file__).parent
PARTS = sorted(p for p in TESTS.iterdir() if p.is_dir() and p.name.startswith("p"))


def test_every_test_file_is_classified():
    for path in TESTS.rglob("test_*.py"):
        assert path.stem.endswith(("_whitebox", "_blackbox")), (
            f"{path.relative_to(TESTS)} must end with _whitebox or _blackbox"
        )


@pytest.mark.parametrize("part", PARTS, ids=lambda p: p.name)
@pytest.mark.parametrize("level", ["unit", "integration"])
@pytest.mark.parametrize("kind", ["whitebox", "blackbox"])
def test_part_has_tests_of_each_level_and_kind(part: Path, level: str, kind: str):
    files = list((part / level).glob(f"test_*_{kind}.py"))
    assert files, f"{part.name} is missing {level} {kind} tests"
