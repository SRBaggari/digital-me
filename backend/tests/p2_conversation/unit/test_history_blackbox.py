"""Spec: conversations hold ordered user/assistant messages; recent context is the last N
exchanges in chronological order; deleting removes a conversation entirely."""

import pytest

from digital_me.conversation import ConversationNotFoundError


def test_messages_returned_in_order(store):
    conv = store.create_conversation()
    for i in range(5):
        store.add_message(conv, "user" if i % 2 == 0 else "assistant", f"m{i}")
    assert [m.content for m in store.get_messages(conv)] == ["m0", "m1", "m2", "m3", "m4"]


def test_message_fields_round_trip(store):
    conv = store.create_conversation()
    saved = store.add_message(conv, "assistant", "Hi ✨", emotion="happy")
    [loaded] = store.get_messages(conv)
    assert loaded == saved
    assert loaded.emotion == "happy" and loaded.interrupted is False


@pytest.mark.parametrize("role", ["system", "tool", "", "User"])
def test_invalid_role_rejected(store, role):
    conv = store.create_conversation()
    with pytest.raises(ValueError):
        store.add_message(conv, role, "x")


@pytest.mark.parametrize("turns, expected", [(1, ["u3", "a3"]), (2, ["u2", "a2", "u3", "a3"]), (10, None)])
def test_recent_messages_window(store, turns, expected):
    conv = store.create_conversation()
    for i in range(1, 4):
        store.add_message(conv, "user", f"u{i}")
        store.add_message(conv, "assistant", f"a{i}")
    contents = [m.content for m in store.recent_messages(conv, turns)]
    assert contents == (expected or ["u1", "a1", "u2", "a2", "u3", "a3"])


def test_conversations_do_not_mix(store):
    a, b = store.create_conversation(), store.create_conversation()
    store.add_message(a, "user", "for a")
    store.add_message(b, "user", "for b")
    assert [m.content for m in store.get_messages(a)] == ["for a"]
    assert [m.content for m in store.recent_messages(b, 5)] == ["for b"]


def test_list_conversations_newest_first_with_counts(store):
    a = store.create_conversation()
    store.add_message(a, "user", "hello a")
    b = store.create_conversation()
    listed = store.list_conversations()
    assert [c.id for c in listed] == [b, a]
    assert listed[1].message_count == 1 and listed[1].title == "hello a"
    assert listed[0].message_count == 0 and listed[0].title is None


def test_latest_conversation(store):
    assert store.latest_conversation_id() is None
    store.create_conversation()
    second = store.create_conversation()
    assert store.latest_conversation_id() == second


def test_delete(store):
    conv = store.create_conversation()
    assert store.delete_conversation(conv) is True
    assert store.delete_conversation(conv) is False
    assert not store.exists(conv)
    with pytest.raises(ConversationNotFoundError):
        store.get_messages(conv)
