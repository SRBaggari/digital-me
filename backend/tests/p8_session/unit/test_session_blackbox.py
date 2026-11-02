"""Spec: on start the client receives the current conversation and an idle state; a user
message produces user_message, emotion, deltas, sentences and assistant_done; interrupt stops
the reply; invalid messages produce bad_request errors."""

import asyncio

import pytest


async def test_start_sends_conversation_then_idle(make_session, recorder):
    session = make_session()
    await session.start()
    assert recorder.events[0] == {
        "type": "conversation",
        "conversation_id": session.conversation_id,
        "messages": [],
    }
    assert recorder.events[1] == {"type": "state", "state": "idle"}


async def test_full_turn_event_order(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(["[happy] Hello! ", "Bye."]))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    assert recorder.types() == [
        "state",
        "user_message",
        "emotion",
        "state",
        "assistant_delta",
        "sentence",  # "Hello!" is complete as soon as the next character arrives
        "assistant_delta",
        "sentence",
        "assistant_done",
        "state",
    ]
    assert recorder.of("emotion")[0]["emotion"] == "happy"
    assert recorder.of("assistant_done")[0]["message"]["content"] == "Hello! Bye."


async def test_interrupt_stops_reply(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(["[neutral] a ", "b ", "c ", "d."], delay=0.05))
    await session.handle({"type": "user_message", "text": "hi"})
    await asyncio.sleep(0.08)
    await session.handle({"type": "interrupt"})
    assert "assistant_interrupted" in recorder.types()
    assert "assistant_done" not in recorder.types()
    assert recorder.events[-1] == {"type": "state", "state": "idle"}


async def test_new_conversation(make_session, recorder, store):
    session = make_session()
    old = session.conversation_id
    await session.handle({"type": "new_conversation"})
    assert session.conversation_id != old
    assert recorder.events[-1]["type"] == "conversation"
    assert recorder.events[-1]["messages"] == []


async def test_open_conversation_returns_history(make_session, recorder, store):
    other = store.create_conversation()
    store.add_message(other, "user", "older chat")
    session = make_session()
    await session.handle({"type": "new_conversation"})
    await session.handle({"type": "open_conversation", "conversation_id": other})
    assert recorder.events[-1]["conversation_id"] == other
    assert recorder.events[-1]["messages"][0]["content"] == "older chat"


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"type": "unknown"},
        {"type": "user_message"},
        {"type": "user_message", "text": 5},
        {"type": "user_message", "text": "x", "extra": True},
        {"type": "open_conversation", "conversation_id": "abc"},
        "just a string",
        None,
    ],
)
async def test_invalid_messages(make_session, recorder, raw):
    await make_session().handle(raw)
    assert recorder.types() == ["error"]
    assert recorder.events[0]["code"] == "bad_request"


async def test_empty_text_reported_as_invalid_input(make_session, recorder):
    session = make_session()
    await session.handle({"type": "user_message", "text": "   "})
    await session.wait_idle()
    assert recorder.of("error")[0]["code"] == "invalid_input"
