"""Listening preferences changed from the UI, stored in the instance's own database."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..config import ListeningSettings
from ..db import Database
from ..preferences import Preferences


class ListeningUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    barge_in: bool | None = None


class ListeningPreferences(Preferences[ListeningSettings]):
    def __init__(self, db: Database, defaults: ListeningSettings):
        super().__init__(db, "listening", defaults, ListeningUpdate)
