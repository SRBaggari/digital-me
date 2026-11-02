"""Spec: personal data, assets and secrets can never be committed; ordinary code can."""

import pytest

# Fake secrets are assembled from pieces so this file itself passes the guard.

@pytest.mark.parametrize(
    "path",
    [
        "instances/alice/profile.yaml",
        "instances/alice/data/digital_me.sqlite3",
        "assets/me.glb",
        "voice/sample.WAV",
        ".env",
        "backend/.env.local",
        "models/whisper.safetensors",
    ],
)
def test_private_paths_blocked(guard, path):
    assert guard.check([path], lambda p: b"") != []


@pytest.mark.parametrize(
    "path",
    ["backend/digital_me/db.py", "instance-template/profile.yaml", ".env.example", "docs/instances.md"],
)
def test_normal_paths_allowed(guard, path):
    assert guard.check([path], lambda p: b"print('hello')") == []


@pytest.mark.parametrize(
    "content",
    [
        "key = 'sk-" + "a" * 32 + "'",
        "ANTHROPIC=sk-ant-" + "b" * 30,
        "token: ghp_" + "c" * 36,
        "-----BEGIN RSA " + "PRIVATE KEY-----",
        "api" + '_key = "abcdefghijklmnop"',
        "AKIA" + "ABCDEFGHIJKLMNOP",
    ],
)
def test_secrets_blocked(guard, content):
    assert guard.check(["config.py"], lambda p: content.encode())


def test_template_and_settings_are_clean(guard, template_dir):
    paths = [str(p) for p in template_dir.iterdir()]
    assert guard.check(paths, lambda p: open(p, "rb").read()) == []


def test_main_exit_codes(guard, tmp_path, capsys):
    good = tmp_path / "ok.py"
    good.write_text("x = 1\n", encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("pass" + 'word = "hunter2hunter2"\n', encoding="utf-8")
    assert guard.main([str(good)]) == 0
    assert guard.main([str(bad)]) == 1
    assert "Commit blocked" in capsys.readouterr().err
