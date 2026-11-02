from pathlib import Path

import pytest

from digital_me.config import instance as inst
from digital_me.config.instance import InstanceError


def test_instances_root_defaults_to_repo_instances(monkeypatch):
    monkeypatch.delenv(inst.HOME_ENV_VAR, raising=False)
    assert inst.instances_root() == inst.REPO_ROOT / "instances"


def test_instances_root_honours_env_override(instances_home):
    assert inst.instances_root() == instances_home.resolve()


def test_repo_root_contains_template():
    assert (inst.REPO_ROOT / "instance-template" / "profile.yaml").is_file()


def test_resolve_rejects_path_escaping_base(tmp_path, monkeypatch):
    # Force the name check to pass so the second (defence-in-depth) check is exercised.
    monkeypatch.setattr(inst, "validate_name", lambda name: name)
    (tmp_path / "base").mkdir()
    with pytest.raises(InstanceError, match="escapes"):
        inst.resolve("../outside", root=tmp_path / "base")


def test_resolve_requires_profile_file(tmp_path):
    (tmp_path / "alice").mkdir()
    with pytest.raises(InstanceError, match="not found"):
        inst.resolve("alice", root=tmp_path)


def test_create_makes_private_subdirectories(tmp_path, template_dir):
    created = inst.create("alice", root=tmp_path, template=template_dir)
    assert created.data_dir.is_dir()
    assert created.avatar_dir.is_dir()
    assert created.voice_dir.is_dir()
    assert created.profile_path.read_text(encoding="utf-8") == (
        template_dir / "profile.yaml"
    ).read_text(encoding="utf-8")


def test_create_fails_when_template_missing(tmp_path):
    with pytest.raises(InstanceError, match="template not found"):
        inst.create("alice", root=tmp_path, template=tmp_path / "nope")


def test_create_refuses_existing_directory(tmp_path, template_dir):
    (tmp_path / "alice").mkdir()
    with pytest.raises(InstanceError, match="already exists"):
        inst.create("alice", root=tmp_path, template=template_dir)


def test_list_instances_missing_root_is_empty(tmp_path):
    assert inst.list_instances(tmp_path / "missing") == []


def test_list_instances_skips_invalid_entries(tmp_path, template_dir):
    inst.create("bob", root=tmp_path, template=template_dir)
    inst.create("alice", root=tmp_path, template=template_dir)
    (tmp_path / "no-profile").mkdir()
    (tmp_path / "Bad Name").mkdir()
    (tmp_path / "Bad Name" / "profile.yaml").write_text("name: x", encoding="utf-8")
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")
    assert inst.list_instances(tmp_path) == ["alice", "bob"]


def test_instance_paths_are_inside_root():
    instance = inst.Instance(name="a", root=Path("/x/a"))
    for path in (
        instance.profile_path,
        instance.settings_path,
        instance.data_dir,
        instance.database_path,
        instance.avatar_dir,
        instance.voice_dir,
    ):
        assert Path("/x/a") in path.parents
