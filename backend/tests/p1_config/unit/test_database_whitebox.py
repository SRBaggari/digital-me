import pytest

from digital_me import db as db_module
from digital_me.db import Database, InstanceMismatchError


def test_fresh_database_is_fully_migrated():
    database = Database(":memory:", "alice")
    assert database.schema_version == len(db_module.MIGRATIONS)
    tables = {r["name"] for r in database.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"meta", "conversations", "messages"} <= tables


def test_owner_written_on_first_open():
    database = Database(":memory:", "alice")
    assert database.query("SELECT value FROM meta WHERE key='instance'")[0]["value"] == "alice"


def test_foreign_keys_enabled():
    database = Database(":memory:", "alice")
    assert database.query("PRAGMA foreign_keys")[0][0] == 1


def test_newer_schema_refused(tmp_path):
    path = tmp_path / "x.sqlite3"
    Database(path, "alice").close()
    raw = Database(path, "alice")
    with raw.transaction() as conn:
        conn.execute("UPDATE meta SET value='999' WHERE key='schema_version'")
    raw.close()
    with pytest.raises(RuntimeError, match="newer"):
        Database(path, "alice")


def test_new_migration_applies_incrementally(tmp_path, monkeypatch):
    path = tmp_path / "x.sqlite3"
    Database(path, "alice").close()
    monkeypatch.setattr(
        db_module, "MIGRATIONS", db_module.MIGRATIONS + ["CREATE TABLE extra (id INTEGER);"]
    )
    database = Database(path, "alice")
    assert database.schema_version == len(db_module.MIGRATIONS)
    assert database.query("SELECT count(*) FROM extra")[0][0] == 0


def test_connection_closed_when_owner_mismatch(tmp_path, monkeypatch):
    path = tmp_path / "x.sqlite3"
    Database(path, "alice").close()
    closed = []
    original = Database._claim_or_verify_owner

    def spy(self):
        closed.append(self._conn)
        original(self)

    monkeypatch.setattr(Database, "_claim_or_verify_owner", spy)
    with pytest.raises(InstanceMismatchError):
        Database(path, "bob")
    with pytest.raises(Exception, match="closed"):
        closed[0].execute("SELECT 1")


def test_transaction_rolls_back_on_error():
    database = Database(":memory:", "alice")
    with pytest.raises(ZeroDivisionError), database.transaction() as conn:
        conn.execute("INSERT INTO conversations (started_at) VALUES ('t')")
        1 / 0
    assert database.query("SELECT count(*) FROM conversations")[0][0] == 0
