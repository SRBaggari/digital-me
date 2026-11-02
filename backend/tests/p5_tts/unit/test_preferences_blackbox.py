"""Spec: settings.yaml gives defaults; changes from the UI persist and are partial updates."""

import pytest
from pydantic import ValidationError

from digital_me.config import VoiceSettings
from digital_me.db import Database
from digital_me.tts import VoicePreferences, VoiceUpdate


@pytest.fixture
def prefs():
    return VoicePreferences(Database(":memory:", "t"), VoiceSettings(voice="af_bella", speed=1.1))


def test_defaults_until_changed(prefs):
    assert prefs.get() == VoiceSettings(voice="af_bella", speed=1.1)


def test_partial_updates_merge(prefs):
    prefs.update(VoiceUpdate(voice="bm_george"))
    prefs.update(VoiceUpdate(speed=0.8))
    assert prefs.get() == VoiceSettings(voice="bm_george", speed=0.8)


def test_disable_voice(prefs):
    assert prefs.update(VoiceUpdate(enabled=False)).enabled is False
    assert prefs.get().enabled is False


def test_changes_survive_reopen(tmp_path):
    path = tmp_path / "db.sqlite3"
    VoicePreferences(Database(path, "t"), VoiceSettings()).update(VoiceUpdate(speed=1.5))
    assert VoicePreferences(Database(path, "t"), VoiceSettings()).get().speed == 1.5


@pytest.mark.parametrize("speed, ok", [(0.5, True), (2.0, True), (0.49, False), (2.01, False)])
def test_speed_bounds(speed, ok):
    if ok:
        assert VoiceUpdate(speed=speed).speed == speed
    else:
        with pytest.raises(ValidationError):
            VoiceUpdate(speed=speed)


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        VoiceUpdate(pitch=3)
