import itertools

import pytest

from digital_me.conversation.history import (
    TITLE_LENGTH,
    ConversationNotFoundError,
    ConversationStore,
    _make_title,
)


@pytest.fixture
def clocked_store(database):
    ticks = (f"2026-01-01T00:00:{i:02d}+00:00" for i in itertools.count())
    return ConversationStore(database, clock=lambda: next(ticks))


def test_clock_is_used_for_timestamps(clocked_store):
    conv = clocked_store.create_conversation()
    message = clocked_store.add_message(conv, "user", "hi")
    assert message.created_at == "2026-01-01T00:00:01+00:00"


def test_title_only_set_from_first_user_message(clocked_store, database):
    conv = clocked_store.create_conversation()
    clocked_store.add_message(conv, "assistant", "greeting")
    assert database.query("SELECT title FROM conversations")[0]["title"] is None
    clocked_store.add_message(conv, "user", "first question")
    clocked_store.add_message(conv, "user", "second question")
    assert database.query("SELECT title FROM conversations")[0]["title"] == "first question"


def test_make_title_collapses_whitespace_and_truncates():
    assert _make_title("  a \n b  ") == "a b"
    long = "word " * 40
    title = _make_title(long)
    assert len(title) <= TITLE_LENGTH and title.endswith("…")


def test_interrupted_flag_stored_as_integer(store, database):
    conv = store.create_conversation()
    store.add_message(conv, "assistant", "partial", interrupted=True)
    assert database.query("SELECT interrupted FROM messages")[0][0] == 1


def test_recent_messages_zero_turns(store):
    conv = store.create_conversation()
    store.add_message(conv, "user", "x")
    assert store.recent_messages(conv, 0) == []


def test_add_message_unknown_conversation_inserts_nothing(store, database):
    with pytest.raises(ConversationNotFoundError):
        store.add_message(999, "user", "hi")
    assert database.query("SELECT count(*) FROM messages")[0][0] == 0


def test_delete_cascades_to_messages(store, database):
    conv = store.create_conversation()
    store.add_message(conv, "user", "x")
    store.delete_conversation(conv)
    assert database.query("SELECT count(*) FROM messages")[0][0] == 0
