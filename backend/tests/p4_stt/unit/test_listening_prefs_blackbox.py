"""Spec: listening settings come from settings.yaml; the UI can switch voice input and barge-in."""

import pytest
from pydantic import ValidationError

from digital_me.config import ListeningSettings, Settings
from digital_me.db import Database
from digital_me.stt import ListeningPreferences, ListeningUpdate


def test_defaults():
    settings = Settings().listening
    assert (settings.enabled, settings.model, settings.language, settings.barge_in) == (True, "base.en", "en", True)


@pytest.mark.parametrize("model", ["base.en", "small.en", "large-v3"])
def test_known_models_accepted(model):
    assert ListeningSettings(model=model).model == model


@pytest.mark.parametrize("model", ["huge", "", "../model"])
def test_unknown_models_rejected(model):
    with pytest.raises(ValidationError):
        ListeningSettings(model=model)


def test_ui_changes_persist(tmp_path):
    path = tmp_path / "db.sqlite3"
    ListeningPreferences(Database(path, "t"), ListeningSettings()).update(ListeningUpdate(barge_in=False))
    assert ListeningPreferences(Database(path, "t"), ListeningSettings()).get().barge_in is False
