"""Spec: Telugu-script text is Telugu, Latin text is English; replies follow the user's language."""

import pytest

from digital_me.conversation import TurnCompleted
from digital_me.language import LANGUAGES, detect_language, reply_instruction


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello, how are you?", "en"),
        ("మీకు ఏ సంగీతం ఇష్టం?", "te"),
        ("నాకు jazz అంటే ఇష్టం", "te"),  # Telugu with an English word
        ("I said నమస్కారం to everyone at the party today", "en"),  # one Telugu word in English
        ("12345 !?", None),
        ("", None),
        ("😊", None),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_supported_languages():
    assert LANGUAGES == {"en": "English", "te": "Telugu"}


def test_telugu_instruction_asks_for_telugu_script():
    instruction = reply_instruction("te")
    assert "Telugu" in instruction and "తెలుగు" in instruction
    assert "[happy]" in instruction  # emotion tags stay machine-readable


async def test_telugu_message_gets_telugu_instruction(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory(["[happy] నా పిల్లి పేరు మిసో."])
    events = await collect(make_engine(llm).respond(store.create_conversation(), "మీ పిల్లి పేరు ఏమిటి?"))
    assert llm.calls[0]["messages"][-2] == {"role": "system", "content": reply_instruction("te")}
    assert isinstance(events[-1], TurnCompleted)
    assert events[-1].message.content == "నా పిల్లి పేరు మిసో."


async def test_english_message_gets_english_instruction(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory()
    await collect(make_engine(llm).respond(store.create_conversation(), "What's your cat called?"))
    assert llm.calls[0]["messages"][-2]["content"] == reply_instruction("en")


async def test_spoken_language_overrides_script(make_engine, store, fake_llm_factory, collect):
    # e.g. Telugu speech that recognition returned in Latin letters
    llm = fake_llm_factory()
    await collect(make_engine(llm).respond(store.create_conversation(), "ela unnavu", language="te"))
    assert llm.calls[0]["messages"][-2]["content"] == reply_instruction("te")


async def test_switching_language_mid_conversation(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory()
    engine = make_engine(llm)
    conv = store.create_conversation()
    await collect(engine.respond(conv, "Hi there"))
    await collect(engine.respond(conv, "బాగున్నారా?"))
    await collect(engine.respond(conv, "Back to English"))
    instructions = [call["messages"][-2]["content"] for call in llm.calls]
    assert instructions == [reply_instruction("en"), reply_instruction("te"), reply_instruction("en")]
