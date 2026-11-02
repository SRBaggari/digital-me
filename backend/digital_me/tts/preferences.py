"""Voice preferences changed from the UI, stored in the instance's own database."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..config.settings import VoiceSettings
from ..db import Database
from ..preferences import Preferences


class VoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    voice: str | None = Field(default=None, min_length=1, max_length=64)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)


class VoicePreferences(Preferences[VoiceSettings]):
    """Defaults come from settings.yaml; changes made in the UI override them."""

    def __init__(self, db: Database, defaults: VoiceSettings):
        super().__init__(db, "voice", defaults, VoiceUpdate)
