"""Spec: `init` creates an instance, `list` prints them, errors exit with status 1."""

from digital_me.__main__ import main


def test_init_then_list(instances_home, capsys):
    assert main(["init", "alice"]) == 0
    assert "profile.yaml" in capsys.readouterr().out
    assert main(["list"]) == 0
    assert capsys.readouterr().out.split() == ["alice"]


def test_init_duplicate_fails(instances_home, capsys):
    main(["init", "alice"])
    assert main(["init", "alice"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_init_invalid_name_fails(instances_home, capsys):
    assert main(["init", "Bad Name"]) == 1
    assert "Invalid instance name" in capsys.readouterr().err


def test_serve_unknown_instance_fails(instances_home, capsys):
    assert main(["serve", "--instance", "ghost"]) == 1
    assert "not found" in capsys.readouterr().err


def test_list_empty(instances_home, capsys):
    assert main(["list"]) == 0
    assert capsys.readouterr().out == ""
