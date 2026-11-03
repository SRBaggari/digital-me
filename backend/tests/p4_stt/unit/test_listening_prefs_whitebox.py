import json

import pytest
from pydantic import ValidationError

from digital_me.config import ListeningSettings
from digital_me.db import Database
from digital_me.stt import ListeningPreferences, ListeningUpdate


def test_only_ui_fields_stored():
    db = Database(":memory:", "t")
    ListeningPreferences(db, ListeningSettings(model="small.en")).update(ListeningUpdate(barge_in=False))
    stored = json.loads(db.query("SELECT value FROM preferences WHERE key='listening'")[0]["value"])
    assert stored == {"enabled": True, "barge_in": False, "telugu_model": "base"}


def test_model_comes_from_settings_not_ui():
    prefs = ListeningPreferences(Database(":memory:", "t"), ListeningSettings(model="small.en"))
    prefs.update(ListeningUpdate(enabled=False))
    assert prefs.get().model == "small.en"


def test_ui_cannot_change_model():
    with pytest.raises(ValidationError):
        ListeningUpdate(model="tiny.en")
