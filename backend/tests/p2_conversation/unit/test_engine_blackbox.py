"""Spec: one turn saves the user message, streams the reply as sentences with emotions
(default neutral), and saves the reply without tags."""

import pytest

from digital_me.conversation import (
    MAX_INPUT_CHARS,
    ConversationNotFoundError,
    SentenceReady,
    TurnCompleted,
    TurnStarted,
)


async def test_basic_turn(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[happy] Hi! ", "Nice to meet you."])
    conv = store.create_conversation()
    events = await collect(make_engine(llm).respond(conv, "  Hello  "))
    assert events[0] == TurnStarted(conv, store.get_messages(conv)[0])
    sentences = [e for e in events if isinstance(e, SentenceReady)]
    assert [(s.index, s.text, s.emotion) for s in sentences] == [
        (0, "Hi!", "happy"),
        (1, "Nice to meet you.", "happy"),
    ]
    done = events[-1]
    assert isinstance(done, TurnCompleted)
    assert done.message.content == "Hi! Nice to meet you."
    assert done.message.emotion == "happy"
    assert [(m.role, m.content) for m in store.get_messages(conv)] == [
        ("user", "Hello"),
        ("assistant", "Hi! Nice to meet you."),
    ]


async def test_untagged_reply_defaults_to_neutral(make_engine, store, fake_llm_factory, collect):
    events = await collect(make_engine(fake_llm_factory(["Just text."])).respond(store.create_conversation(), "x"))
    assert events[-1].message.emotion == "neutral"
    assert [e.emotion for e in events if isinstance(e, SentenceReady)] == ["neutral"]


async def test_unknown_tag_kept_as_text(make_engine, store, fake_llm_factory, collect):
    events = await collect(
        make_engine(fake_llm_factory(["[grinning] Hi."])).respond(store.create_conversation(), "x")
    )
    assert events[-1].message.content == "[grinning] Hi."


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
async def test_empty_input_rejected(make_engine, store, fake_llm_factory, collect, text):
    with pytest.raises(ValueError):
        await collect(make_engine(fake_llm_factory()).respond(store.create_conversation(), text))


@pytest.mark.parametrize("length, ok", [(MAX_INPUT_CHARS, True), (MAX_INPUT_CHARS + 1, False)])
async def test_input_length_boundary(make_engine, store, fake_llm_factory, collect, length, ok):
    engine = make_engine(fake_llm_factory())
    conv = store.create_conversation()
    if ok:
        assert await collect(engine.respond(conv, "a" * length))
    else:
        with pytest.raises(ValueError):
            await collect(engine.respond(conv, "a" * length))


async def test_unknown_conversation(make_engine, fake_llm_factory, collect):
    with pytest.raises(ConversationNotFoundError):
        await collect(make_engine(fake_llm_factory()).respond(12345, "hi"))


async def test_follow_up_sees_previous_turn(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[neutral] Sure."])
    engine = make_engine(llm)
    conv = store.create_conversation()
    await collect(engine.respond(conv, "My favourite colour is green."))
    await collect(engine.respond(conv, "What did I just say?"))
    contents = [m["content"] for m in llm.calls[1]["messages"]]
    assert "My favourite colour is green." in contents
