"""Against the real local model (skipped if Ollama is not running).

Assertions are deliberately about observable behaviour that a small model reliably shows,
so these tests are not flaky; persona quality is evaluated separately with
backend/scripts/eval_persona.py.
"""

import pytest

from digital_me.config import LLMSettings
from digital_me.conversation import EMOTIONS, ConversationEngine, SentenceReady, TurnCompleted

pytestmark = pytest.mark.live


async def test_real_model_produces_tagged_sentences(live_llm, profile, store, collect):
    engine = ConversationEngine(profile, store, live_llm, LLMSettings(model=live_llm.model, temperature=0.2))
    conv = store.create_conversation()
    events = await collect(engine.respond(conv, "Hi! How are you today?"))

    done = events[-1]
    assert isinstance(done, TurnCompleted)
    assert done.message.content
    assert done.message.emotion in EMOTIONS
    assert "[" not in done.message.content or "]" not in done.message.content
    assert any(isinstance(e, SentenceReady) for e in events)


async def test_real_model_uses_conversation_context(live_llm, profile, store, collect):
    engine = ConversationEngine(profile, store, live_llm, LLMSettings(model=live_llm.model, temperature=0.0))
    conv = store.create_conversation()
    await collect(engine.respond(conv, "Please remember this code word: PINEAPPLE."))
    events = await collect(engine.respond(conv, "What was the code word I just gave you? Answer with just the word."))
    assert "pineapple" in events[-1].message.content.lower()


async def test_real_model_answers_telugu_in_telugu(live_llm, profile, store, collect):
    from digital_me.language import detect_language

    engine = ConversationEngine(profile, store, live_llm, LLMSettings(model=live_llm.model, temperature=0.2))
    conv = store.create_conversation()
    telugu = await collect(engine.respond(conv, "మీ కుక్క పేరు ఏమిటి?"))  # "What is your dog's name?"
    assert detect_language(telugu[-1].message.content) == "te", telugu[-1].message.content
    english = await collect(engine.respond(conv, "And what do you do for work?"))
    assert detect_language(english[-1].message.content) == "en", english[-1].message.content


async def test_real_model_answers_romanised_telugu_in_telugu_script(live_llm, profile, store, collect):
    from digital_me.language import detect_language

    engine = ConversationEngine(profile, store, live_llm, LLMSettings(model=live_llm.model, temperature=0.2))
    events = await collect(engine.respond(store.create_conversation(), "mee kukka peru enti?"))
    reply = events[-1].message.content
    assert detect_language(reply) == "te" and not is_romanised(reply), reply
    assert "[" not in reply, reply  # emotion tags, even Telugu ones, never reach the text


async def test_real_model_never_refuses_telugu(live_llm, profile, store, collect):
    """Regression: 'em chesthunaru' was answered with 'That's Telugu. I don't understand.'"""
    from digital_me.language import detect_language

    engine = ConversationEngine(profile, store, live_llm, LLMSettings(model=live_llm.model, temperature=0.2))
    events = await collect(engine.respond(store.create_conversation(), "em chesthunaru"))
    reply = events[-1].message.content
    assert detect_language(reply) == "te", reply
    assert "understand" not in reply.lower(), reply


def is_romanised(text):
    return not any(0x0C00 <= ord(c) <= 0x0C7F for c in text)


async def test_real_model_knows_profile_fact(live_llm, profile, store, collect):
    engine = ConversationEngine(profile, store, live_llm, LLMSettings(model=live_llm.model, temperature=0.0))
    conv = store.create_conversation()
    events = await collect(engine.respond(conv, "What is your dog's name?"))
    assert "pixel" in events[-1].message.content.lower()
