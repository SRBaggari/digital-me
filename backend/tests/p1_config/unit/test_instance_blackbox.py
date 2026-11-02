"""Spec: instance names are 1-32 chars of [a-z0-9_-], starting with [a-z0-9]."""

import pytest

from digital_me.config import InstanceError, create, list_instances, resolve, validate_name


@pytest.mark.parametrize("name", ["a", "0", "alice", "bob-2", "x_y", "a" * 32])
def test_valid_names_accepted(name):
    assert validate_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",  # empty
        "a" * 33,  # one over the limit
        "Alice",  # uppercase
        "-alice",  # leading dash
        "_alice",  # leading underscore
        "al ice",  # space
        "../etc",  # traversal
        "a/b",
        "a\\b",
        ".",
        "..",
        "ali.ce",
        None,
        42,
    ],
)
def test_invalid_names_rejected(name):
    with pytest.raises(InstanceError):
        validate_name(name)


def test_create_then_resolve_round_trip(instances_home):
    created = create("alice")
    resolved = resolve("alice")
    assert resolved == created
    assert resolved.name == "alice"


def test_resolve_unknown_instance_fails(instances_home):
    with pytest.raises(InstanceError):
        resolve("ghost")


def test_create_twice_fails(instances_home):
    create("alice")
    with pytest.raises(InstanceError):
        create("alice")


def test_list_instances_reports_created(instances_home):
    assert list_instances() == []
    create("bob")
    create("alice")
    assert list_instances() == ["alice", "bob"]


def test_two_instances_never_share_paths(instances_home):
    a, b = create("alice"), create("bob")
    assert a.root != b.root
    assert a.database_path != b.database_path
    assert not a.root.is_relative_to(b.root) and not b.root.is_relative_to(a.root)
