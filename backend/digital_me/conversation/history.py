"""Persistent conversation history for one instance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from ..db import Database

ROLES = ("user", "assistant")
TITLE_LENGTH = 60


class ConversationNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    emotion: str | None
    interrupted: bool
    created_at: str


@dataclass(frozen=True)
class Conversation:
    id: int
    started_at: str
    title: str | None
    message_count: int


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ConversationStore:
    def __init__(self, db: Database, clock: Callable[[], str] = _utc_now):
        self._db = db
        self._clock = clock

    def create_conversation(self) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO conversations (started_at) VALUES (?)", (self._clock(),)
            )
            return int(cursor.lastrowid)

    def exists(self, conversation_id: int) -> bool:
        return bool(self._db.query("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)))

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        *,
        emotion: str | None = None,
        interrupted: bool = False,
    ) -> Message:
        if role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}, got {role!r}")
        created_at = self._clock()
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT title FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row is None:
                raise ConversationNotFoundError(conversation_id)
            cursor = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, emotion, interrupted, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, role, content, emotion, int(interrupted), created_at),
            )
            if row["title"] is None and role == "user":
                conn.execute(
                    "UPDATE conversations SET title = ? WHERE id = ?",
                    (_make_title(content), conversation_id),
                )
        return Message(
            id=int(cursor.lastrowid),
            conversation_id=conversation_id,
            role=role,
            content=content,
            emotion=emotion,
            interrupted=interrupted,
            created_at=created_at,
        )

    def get_messages(self, conversation_id: int) -> list[Message]:
        if not self.exists(conversation_id):
            raise ConversationNotFoundError(conversation_id)
        rows = self._db.query(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        )
        return [_row_to_message(r) for r in rows]

    def recent_messages(self, conversation_id: int, max_turns: int) -> list[Message]:
        """The last `max_turns` user/assistant exchanges, oldest first."""
        if max_turns <= 0:
            return []
        rows = self._db.query(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, max_turns * 2),
        )
        return [_row_to_message(r) for r in reversed(rows)]

    def list_conversations(self) -> list[Conversation]:
        rows = self._db.query(
            "SELECT c.id, c.started_at, c.title, COUNT(m.id) AS message_count "
            "FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id "
            "GROUP BY c.id ORDER BY c.id DESC"
        )
        return [
            Conversation(
                id=r["id"],
                started_at=r["started_at"],
                title=r["title"],
                message_count=r["message_count"],
            )
            for r in rows
        ]

    def latest_conversation_id(self) -> int | None:
        rows = self._db.query("SELECT id FROM conversations ORDER BY id DESC LIMIT 1")
        return rows[0]["id"] if rows else None

    def delete_conversation(self, conversation_id: int) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0


def _make_title(content: str) -> str:
    text = " ".join(content.split())
    return text if len(text) <= TITLE_LENGTH else text[: TITLE_LENGTH - 1].rstrip() + "…"


def _row_to_message(row) -> Message:
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        emotion=row["emotion"],
        interrupted=bool(row["interrupted"]),
        created_at=row["created_at"],
    )
