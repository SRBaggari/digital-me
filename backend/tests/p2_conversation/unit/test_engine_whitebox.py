import pytest

from digital_me.conversation import (
    EmotionChanged,
    SentenceReady,
    TextDelta,
    TurnCompleted,
    TurnStarted,
)
from digital_me.language import reply_instruction
from digital_me.llm import LLMError


async def test_history_window_passed_to_llm(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory()
    engine = make_engine(llm, context_turns=1)
    conv = store.create_conversation()
    for i in range(3):
        store.add_message(conv, "user", f"u{i}")
        store.add_message(conv, "assistant", f"a{i}", emotion="happy")
    await collect(engine.respond(conv, "new"))
    messages = llm.calls[0]["messages"]
    assert [m["content"] for m in messages[1:]] == ["u2", "[happy] a2", reply_instruction("en"), "new"]


async def test_settings_forwarded(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory()
    await collect(make_engine(llm, temperature=0.2, num_ctx=1024).respond(store.create_conversation(), "x"))
    assert llm.calls[0]["temperature"] == 0.2 and llm.calls[0]["num_ctx"] == 1024


async def test_tag_split_across_chunks(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[sur", "prised] Oh", " wow!"])
    events = await collect(make_engine(llm).respond(store.create_conversation(), "x"))
    assert EmotionChanged("surprised") in events
    assert [e.text for e in events if isinstance(e, TextDelta)] == ["Oh", " wow!"]


async def test_emotion_change_flushes_pending_sentence(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[happy] Great", "[serious] But careful."])
    events = await collect(make_engine(llm).respond(store.create_conversation(), "x"))
    sentences = [(e.text, e.emotion) for e in events if isinstance(e, SentenceReady)]
    assert sentences == [("Great", "happy"), ("But careful.", "serious")]


async def test_repeated_same_tag_not_reemitted(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[sad] One. [sad] Two."])
    events = await collect(make_engine(llm).respond(store.create_conversation(), "x"))
    assert [e for e in events if isinstance(e, EmotionChanged)] == [EmotionChanged("sad")]


async def test_double_spaces_collapsed_in_saved_text(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[neutral] One. [happy] Two."])
    events = await collect(make_engine(llm).respond(store.create_conversation(), "x"))
    assert events[-1].message.content == "One. Two."


async def test_partial_reply_saved_as_interrupted_on_error(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[happy] Partial", " answer", " more"], fail_after=2)
    conv = store.create_conversation()
    with pytest.raises(LLMError):
        await collect(make_engine(llm).respond(conv, "x"))
    saved = store.get_messages(conv)
    assert [(m.role, m.content, m.interrupted, m.emotion) for m in saved] == [
        ("user", "x", False, None),
        ("assistant", "Partial answer", True, "happy"),
    ]


async def test_nothing_saved_for_assistant_when_error_before_text(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[happy]"], fail_after=0)
    conv = store.create_conversation()
    with pytest.raises(LLMError):
        await collect(make_engine(llm).respond(conv, "x"))
    assert [m.role for m in store.get_messages(conv)] == ["user"]


async def test_empty_reply_is_an_error(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[neutral]", "   "])
    with pytest.raises(LLMError, match="empty"):
        await collect(make_engine(llm).respond(store.create_conversation(), "x"))


async def test_closing_generator_early_saves_interrupted(make_engine, store, fake_llm_factory):
    llm = fake_llm_factory(["[neutral] First. ", "Second. ", "Third."])
    conv = store.create_conversation()
    stream = make_engine(llm).respond(conv, "x")
    async for event in stream:
        if isinstance(event, SentenceReady):
            break
    await stream.aclose()
    reply = store.get_messages(conv)[-1]
    assert reply.interrupted and reply.content == "First."


async def test_event_sequence_shape(make_engine, store, fake_llm_factory, collect):
    events = await collect(make_engine(fake_llm_factory()).respond(store.create_conversation(), "x"))
    assert isinstance(events[0], TurnStarted)
    assert isinstance(events[1], EmotionChanged)
    assert isinstance(events[-1], TurnCompleted)
