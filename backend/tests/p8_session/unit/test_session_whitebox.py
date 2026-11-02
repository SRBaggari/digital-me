import asyncio

from digital_me.llm import LLMError
from digital_me.server import Session


async def test_new_session_reuses_latest_conversation(make_session, store):
    existing = store.create_conversation()
    assert make_session().conversation_id == existing


async def test_new_session_creates_conversation_when_none(make_session, store):
    session = make_session()
    assert store.exists(session.conversation_id)


async def test_state_transitions_for_a_turn(make_session, recorder):
    session = make_session()
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    states = [e["state"] for e in recorder.of("state")]
    assert states == ["thinking", "speaking", "idle"]


async def test_speaking_state_sent_once_per_turn(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(["[neutral] a", "b", "c."]))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    assert [e["state"] for e in recorder.of("state")].count("speaking") == 1


async def test_new_message_cancels_running_turn(make_session, recorder, fake_llm_factory, store):
    session = make_session(fake_llm_factory(["[neutral] one ", "two ", "three."], delay=0.05))
    await session.handle({"type": "user_message", "text": "first"})
    await asyncio.sleep(0.07)
    await session.handle({"type": "user_message", "text": "second"})
    await session.wait_idle()
    assert recorder.types().count("assistant_interrupted") == 1
    messages = store.get_messages(session.conversation_id)
    assert [m.content for m in messages if m.role == "user"] == ["first", "second"]
    assert messages[1].interrupted is True
    assert messages[-1].interrupted is False


async def test_interrupt_without_turn_is_noop(make_session, recorder):
    session = make_session()
    await session.handle({"type": "interrupt"})
    assert recorder.events == []
    assert not session.busy


async def test_llm_error_reported_and_state_idle(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(fail_after=0, error=LLMError("offline")))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    [error] = recorder.of("error")
    assert error["code"] == "llm_error" and "offline" in error["detail"]
    assert recorder.events[-1] == {"type": "state", "state": "idle"}


async def test_unexpected_error_does_not_leak_details(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(fail_after=0, error=RuntimeError("secret path C:\\x")))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    [error] = recorder.of("error")
    assert error["code"] == "internal_error" and "secret" not in error["detail"]


async def test_send_failure_marks_closed_and_stops_sending(make_context, store):
    calls = []

    async def broken_send(event):
        calls.append(event)
        raise RuntimeError("socket gone")

    session = Session(make_context().engine, store, broken_send)
    await session.start()
    assert len(calls) == 1  # second send skipped after first failure
    assert session._closed


async def test_close_cancels_turn_silently(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(["[neutral] slow ", "reply."], delay=0.2))
    await session.handle({"type": "user_message", "text": "hi"})
    await asyncio.sleep(0.01)
    await session.close()
    assert not session.busy
    assert "assistant_interrupted" not in recorder.types()


async def test_open_missing_conversation_keeps_current(make_session, recorder):
    session = make_session()
    current = session.conversation_id
    await session.handle({"type": "open_conversation", "conversation_id": 9999})
    assert session.conversation_id == current
    assert recorder.of("error")[0]["code"] == "not_found"
