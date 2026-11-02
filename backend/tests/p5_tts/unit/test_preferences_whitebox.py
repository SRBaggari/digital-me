import json

from digital_me.config import VoiceSettings
from digital_me.db import Database
from digital_me.tts import VoicePreferences, VoiceUpdate


def make():
    db = Database(":memory:", "t")
    return db, VoicePreferences(db, VoiceSettings(voice="af_heart"))


def test_only_user_fields_are_stored():
    db, prefs = make()
    prefs.update(VoiceUpdate(speed=1.2))
    stored = json.loads(db.query("SELECT value FROM preferences WHERE key='voice'")[0]["value"])
    assert stored == {"enabled": True, "voice": "af_heart", "speed": 1.2}


def test_corrupt_row_falls_back_to_defaults():
    db, prefs = make()
    with db.transaction() as conn:
        conn.execute("INSERT INTO preferences VALUES ('voice', '{not json')")
    assert prefs.get() == VoiceSettings(voice="af_heart")


def test_out_of_range_stored_value_falls_back():
    db, prefs = make()
    with db.transaction() as conn:
        conn.execute("""INSERT INTO preferences VALUES ('voice', '{"speed": 99}')""")
    assert prefs.get().speed == 1.0


def test_update_upserts_single_row():
    db, prefs = make()
    prefs.update(VoiceUpdate(enabled=False))
    prefs.update(VoiceUpdate(voice="bm_george"))
    assert db.query("SELECT count(*) FROM preferences")[0][0] == 1
