"""SQLite access with an instance-ownership guard and ordered schema migrations."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Append-only: each entry upgrades the schema by one version. Never edit old entries.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY,
        started_at TEXT NOT NULL,
        title TEXT
    );
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        emotion TEXT,
        interrupted INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    CREATE INDEX idx_messages_conversation ON messages(conversation_id, id);
    """,
]


class InstanceMismatchError(Exception):
    """The database belongs to a different Digital Me instance."""


class Database:
    """Thread-safe wrapper around one SQLite file owned by exactly one instance."""

    def __init__(self, path: Path | str, instance_name: str):
        self.path = Path(path) if path != ":memory:" else path
        self.instance_name = instance_name
        if isinstance(self.path, Path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        try:
            self._claim_or_verify_owner()
            self._migrate()
        except Exception:
            self._conn.close()
            raise

    def _claim_or_verify_owner(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = self._conn.execute("SELECT value FROM meta WHERE key = 'instance'").fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES ('instance', ?)", (self.instance_name,)
                )
            elif row["value"] != self.instance_name:
                raise InstanceMismatchError(
                    f"Database {self.path} belongs to instance {row['value']!r}, "
                    f"not {self.instance_name!r}. Refusing to open it."
                )

    @property
    def schema_version(self) -> int:
        row = self._conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row["value"]) if row else 0

    def _migrate(self) -> None:
        with self._lock:
            current = self.schema_version
            if current > len(MIGRATIONS):
                raise RuntimeError(
                    f"Database schema v{current} is newer than this code supports (v{len(MIGRATIONS)})"
                )
            for version, script in enumerate(MIGRATIONS[current:], start=current + 1):
                # executescript commits implicitly, so the version bump runs right after it.
                self._conn.executescript(script)
                with self._conn:
                    self._conn.execute(
                        "INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (str(version),),
                    )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._conn:
            yield self._conn

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
