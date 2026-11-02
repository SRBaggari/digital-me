"""Real filesystem + real SQLite: two instances must stay completely separate."""

import sqlite3

from digital_me.config import create, load_profile
from digital_me.db import Database


def test_each_instance_database_is_stamped_with_its_owner(instances_home):
    alice, bob = create("alice"), create("bob")
    Database(alice.database_path, alice.name).close()
    Database(bob.database_path, bob.name).close()
    for instance in (alice, bob):
        raw = sqlite3.connect(instance.database_path)
        owner = raw.execute("SELECT value FROM meta WHERE key='instance'").fetchone()[0]
        raw.close()
        assert owner == instance.name


def test_writes_to_one_instance_do_not_touch_the_other(instances_home):
    alice, bob = create("alice"), create("bob")
    db_a = Database(alice.database_path, alice.name)
    db_b = Database(bob.database_path, bob.name)
    with db_a.transaction() as conn:
        conn.execute("INSERT INTO conversations (started_at) VALUES ('t')")
    assert db_a.query("SELECT count(*) FROM conversations")[0][0] == 1
    assert db_b.query("SELECT count(*) FROM conversations")[0][0] == 0


def test_profile_edit_is_local_to_instance(instances_home):
    alice, bob = create("alice"), create("bob")
    alice.profile_path.write_text("name: Alice\n", encoding="utf-8")
    assert load_profile(alice.profile_path).name == "Alice"
    assert load_profile(bob.profile_path).name != "Alice"
