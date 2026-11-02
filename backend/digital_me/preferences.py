"""Settings changed from the UI, stored per instance in its own database.

settings.yaml provides the defaults; UI changes override them field by field.
"""

from __future__ import annotations

import json
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from .db import Database

S = TypeVar("S", bound=BaseModel)


class Preferences(Generic[S]):
    def __init__(self, db: Database, key: str, defaults: S, update_model: type[BaseModel]):
        self._db = db
        self._key = key
        self._defaults = defaults
        self._update_model = update_model
        self._fields = set(update_model.model_fields)

    def get(self) -> S:
        rows = self._db.query("SELECT value FROM preferences WHERE key = ?", (self._key,))
        if not rows:
            return self._defaults
        try:
            stored = self._update_model.model_validate(json.loads(rows[0]["value"]))
        except (ValueError, ValidationError):
            return self._defaults  # unreadable row: fall back rather than break the feature
        return self._defaults.model_copy(update=stored.model_dump(exclude_none=True))

    def update(self, change: BaseModel) -> S:
        merged = self.get().model_copy(update=change.model_dump(exclude_none=True))
        value = json.dumps(merged.model_dump(include=self._fields))
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (self._key, value),
            )
        return merged
