"""Spec: a database belongs to the first instance that opens it; others are refused."""

import pytest

from digital_me.db import Database, InstanceMismatchError


def test_same_instance_can_reopen(tmp_path):
    path = tmp_path / "data" / "db.sqlite3"
    Database(path, "alice").close()
    Database(path, "alice").close()


def test_other_instance_is_refused(tmp_path):
    path = tmp_path / "db.sqlite3"
    Database(path, "alice").close()
    with pytest.raises(InstanceMismatchError):
        Database(path, "bob")


def test_parent_directory_created(tmp_path):
    path = tmp_path / "deep" / "nested" / "db.sqlite3"
    Database(path, "alice").close()
    assert path.is_file()


def test_data_survives_reopen(tmp_path):
    path = tmp_path / "db.sqlite3"
    first = Database(path, "alice")
    with first.transaction() as conn:
        conn.execute("INSERT INTO conversations (started_at) VALUES ('2026-01-01')")
    first.close()
    second = Database(path, "alice")
    assert second.query("SELECT count(*) FROM conversations")[0][0] == 1
