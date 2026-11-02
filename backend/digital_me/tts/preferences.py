"""Voice preferences changed from the UI, stored in the instance's own database."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from ..config.settings import VoiceSettings
from ..db import Database

KEY = "voice"


class VoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    voice: str | None = Field(default=None, min_length=1, max_length=64)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)


class VoicePreferences:
    """Defaults come from settings.yaml; changes made in the UI override them."""

    def __init__(self, db: Database, defaults: VoiceSettings):
        self._db = db
        self._defaults = defaults

    def get(self) -> VoiceSettings:
        rows = self._db.query("SELECT value FROM preferences WHERE key = ?", (KEY,))
        if not rows:
            return self._defaults
        try:
            stored = json.loads(rows[0]["value"])
            return self._defaults.model_copy(update=VoiceUpdate.model_validate(stored).model_dump(exclude_none=True))
        except ValueError:
            return self._defaults  # unreadable row: fall back rather than break speech

    def update(self, change: VoiceUpdate) -> VoiceSettings:
        merged = self.get().model_copy(update=change.model_dump(exclude_none=True))
        value = json.dumps(merged.model_dump(include={"enabled", "voice", "speed"}))
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (KEY, value),
            )
        return merged
