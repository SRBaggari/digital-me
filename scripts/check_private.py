"""Pre-commit guard for a public repository: refuse to commit personal data or secrets.

Usage:
    python scripts/check_private.py            # checks staged files (used by the git hook)
    python scripts/check_private.py FILE ...   # checks the given files
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import PurePosixPath

BLOCKED_DIRS = ("instances/",)
BLOCKED_NAMES = re.compile(r"(^|/)\.env(\.[^/]*)?$")
ALLOWED_NAMES = re.compile(r"(^|/)\.env\.example$")
BLOCKED_SUFFIXES = {
    ".glb", ".gltf", ".vrm", ".fbx", ".blend",  # avatar assets
    ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm",  # voice recordings
    ".sqlite", ".sqlite3", ".db",  # memories and conversations
    ".onnx", ".pt", ".pth", ".safetensors",  # model weights
}
SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("ElevenLabs/HF token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    (
        "hard-coded secret",
        re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
    ),
]
MAX_TEXT_BYTES = 2_000_000


def path_problem(path: str) -> str | None:
    posix = PurePosixPath(path.replace("\\", "/"))
    text = str(posix)
    if any(text == d.rstrip("/") or text.startswith(d) for d in BLOCKED_DIRS):
        return "private instance data (instances/ is personal and must stay local)"
    if BLOCKED_NAMES.search(text) and not ALLOWED_NAMES.search(text):
        return "environment file (may contain secrets)"
    if posix.suffix.lower() in BLOCKED_SUFFIXES:
        return f"{posix.suffix} files may contain voice, likeness, memories or model weights"
    return None


def content_problems(content: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS if pattern.search(content)]


def check(paths: list[str], read) -> list[str]:
    """Return a list of human-readable problems. `read(path)` returns bytes or None."""
    problems = []
    for path in paths:
        if reason := path_problem(path):
            problems.append(f"{path}: {reason}")
            continue
        data = read(path)
        if data is None or len(data) > MAX_TEXT_BYTES or b"\0" in data[:8192]:
            continue  # deleted, huge or binary
        for name in content_problems(data.decode("utf-8", errors="replace")):
            problems.append(f"{path}: looks like it contains a {name}")
    return problems


def _staged_paths() -> list[str]:
    output = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        capture_output=True, check=True,
    ).stdout
    return [p for p in output.decode().split("\0") if p]


def _read_staged(path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f":{path}"], capture_output=True)
    return result.stdout if result.returncode == 0 else None


def _read_file(path: str) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def main(argv: list[str]) -> int:
    if argv:
        problems = check(argv, _read_file)
    else:
        problems = check(_staged_paths(), _read_staged)
    if problems:
        print("Commit blocked: this repository is public.\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("\nKeep personal data under instances/ (git-ignored).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
