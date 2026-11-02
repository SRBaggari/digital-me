"""Spec: with voice on, every reply sentence also arrives as audio (in order), followed by
speech_end, before the session goes idle. With voice off, no audio is sent. Interrupting stops speech."""

import asyncio

import pytest
from hypothesis import given
from hypothesis import strategies as st

from digital_me.server.speech import speakable_chunks

@given(
    st.lists(
        st.tuples(st.text(alphabet="abcdefg", min_size=1, max_size=6), st.sampled_from(["", "", ",", ";", " —"])),
        min_size=1,
        max_size=40,
    ),
    st.booleans(),
)
def test_chunks_never_lose_or_reorder_words(pieces, first):
    text = " ".join(word + punct for word, punct in pieces)
    chunks = speakable_chunks(text, first)
    assert " ".join(chunks).split() == text.split()
    assert all(chunk.strip() for chunk in chunks)


@pytest.mark.parametrize("first, limit", [(True, 8), (False, 16)])
def test_short_sentences_are_spoken_whole(first, limit):
    text = ", ".join(["word"] * limit)
    assert speakable_chunks(text, first) == [text]


def test_long_first_sentence_starts_with_a_short_clause():
    text = "Miso is my cat, and she spends most of her days lounging in the sun by the window."
    chunks = speakable_chunks(text, first=True)
    assert chunks[0] == "Miso is my cat,"
    assert len(chunks) == 2


async def test_reply_is_spoken_sentence_by_sentence(make_session, make_speech, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(["[happy] Hello there! ", "How are you?"]), make_speech())
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    audio = recorder.of("audio")
    assert [a["text"] for a in audio] == ["Hello there!", "How are you?"]
    types = recorder.types()
    assert types.index("speech_end") < len(types) - 1
    assert recorder.events[-1] == {"type": "state", "state": "idle"}


async def test_voice_disabled_sends_no_audio(make_session, make_speech, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(), make_speech(enabled=False))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    assert "audio" not in recorder.types() and "speech_end" not in recorder.types()


async def test_no_speech_configured_behaves_like_text_only(make_session, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory())
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    assert "audio" not in recorder.types()


async def test_interrupt_stops_speech(make_session, make_speech, recorder, fake_llm_factory, fake_tts_factory):
    tts = fake_tts_factory(delay=0.15)
    session = make_session(fake_llm_factory(["[neutral] One. ", "Two. ", "Three. ", "Four."]), make_speech(tts))
    await session.handle({"type": "user_message", "text": "count"})
    await asyncio.sleep(0.05)
    await session.handle({"type": "interrupt"})
    await asyncio.sleep(0.4)
    assert len(recorder.of("audio")) < 4
    assert "speech_end" not in recorder.types()


async def test_speech_failure_does_not_break_text(make_session, make_speech, recorder, fake_llm_factory, fake_tts_factory):
    session = make_session(fake_llm_factory(["[neutral] Hello."]), make_speech(fake_tts_factory(fail_on="Hello")))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    assert recorder.of("assistant_done")[0]["message"]["content"] == "Hello."
    assert recorder.of("error")[0]["code"] == "tts_error"
