"""Spec: copying or pointing one instance at another's database must fail loudly."""

import shutil

import pytest

from digital_me.config import create, resolve
from digital_me.db import Database, InstanceMismatchError


def test_copied_database_cannot_be_used_by_another_instance(instances_home):
    alice, bob = create("alice"), create("bob")
    Database(alice.database_path, alice.name).close()
    shutil.copy(alice.database_path, bob.database_path)
    with pytest.raises(InstanceMismatchError):
        Database(bob.database_path, bob.name)


def test_resolved_instance_reopens_its_own_database(instances_home):
    create("alice")
    alice = resolve("alice")
    Database(alice.database_path, alice.name).close()
    Database(resolve("alice").database_path, "alice").close()
