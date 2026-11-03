"""Spec: with the microphone on, speaking a sentence sends it as a message and Digital Me replies;
talking while it is replying interrupts it (barge-in), unless barge-in is switched off."""

import asyncio


async def say(session, speech_audio, ms=800, pause=900):
    await session.handle_audio(speech_audio.voice(ms))
    await session.handle_audio(speech_audio.silence(pause))


async def settle(seconds=0.05):
    await asyncio.sleep(seconds)


async def test_spoken_sentence_becomes_a_conversation_turn(make_session, make_hearing, fake_transcriber_factory, recorder, speech_audio, fake_llm_factory, store):
    session = make_session(fake_llm_factory(["[happy] Hi!"]), hearing=make_hearing(fake_transcriber_factory(["What's up?"])))
    await session.handle({"type": "mic_start"})
    await say(session, speech_audio)
    await settle()
    await session.wait_idle()
    types = recorder.types()
    assert types[:4] == ["mic", "user_speaking", "user_speaking", "transcribing"]
    assert recorder.of("transcript") == [{"type": "transcript", "text": "What's up?", "language": None}]
    assert recorder.of("user_message")[0]["message"]["content"] == "What's up?"
    assert recorder.of("assistant_done")[0]["message"]["content"] == "Hi!"
    assert [m.content for m in store.get_messages(session.conversation_id)] == ["What's up?", "Hi!"]


async def test_audio_ignored_while_mic_is_off(make_session, make_hearing, recorder, speech_audio):
    session = make_session(hearing=make_hearing())
    await say(session, speech_audio)
    assert recorder.events == []


async def test_mic_stop(make_session, make_hearing, recorder, speech_audio):
    session = make_session(hearing=make_hearing())
    await session.handle({"type": "mic_start"})
    await session.handle({"type": "mic_stop"})
    await say(session, speech_audio)
    assert recorder.types() == ["mic", "mic"]
    assert recorder.events[-1] == {"type": "mic", "on": False}


async def test_mic_unavailable_without_speech_recognition(make_session, recorder):
    await make_session().handle({"type": "mic_start"})
    assert recorder.events == [{"type": "error", "code": "not_available", "detail": "Voice input is not available"}]


async def test_mic_refused_when_switched_off(make_session, make_hearing, recorder):
    await make_session(hearing=make_hearing(enabled=False)).handle({"type": "mic_start"})
    assert recorder.events[0]["code"] == "not_available"


async def test_talking_over_the_reply_interrupts_it(make_session, make_hearing, recorder, speech_audio, fake_llm_factory):
    llm = fake_llm_factory(["[neutral] One. ", "Two. ", "Three. ", "Four. ", "Five."], delay=0.1)
    session = make_session(llm, hearing=make_hearing())
    await session.handle({"type": "mic_start"})
    await session.handle({"type": "user_message", "text": "count"})
    await settle(0.15)
    await session.handle_audio(speech_audio.voice(400))
    assert "assistant_interrupted" in recorder.types()
    assert {"type": "barge_in"} in recorder.events


async def test_talking_while_reply_is_only_audible_also_interrupts(make_session, make_hearing, recorder, speech_audio):
    session = make_session(hearing=make_hearing())
    await session.handle({"type": "mic_start"})
    await session.handle({"type": "playback", "playing": True})
    await session.handle_audio(speech_audio.voice(600))
    assert {"type": "barge_in"} in recorder.events


async def test_without_barge_in_speech_during_reply_is_ignored(make_session, make_hearing, recorder, speech_audio, fake_llm_factory):
    session = make_session(fake_llm_factory(), hearing=make_hearing(barge_in=False))
    await session.handle({"type": "mic_start"})
    await session.handle({"type": "playback", "playing": True})
    await say(session, speech_audio, ms=700)
    await settle()
    assert "barge_in" not in recorder.types()
    assert recorder.of("user_message") == []


async def test_empty_transcript_starts_no_turn(make_session, make_hearing, fake_transcriber_factory, recorder, speech_audio):
    session = make_session(hearing=make_hearing(fake_transcriber_factory([""])))
    await session.handle({"type": "mic_start"})
    await say(session, speech_audio)
    await settle()
    assert recorder.of("transcript") == [{"type": "transcript", "text": "", "language": None}]
    assert recorder.of("user_message") == []


async def test_one_word_answer_is_heard(make_session, make_hearing, fake_transcriber_factory, recorder, speech_audio, fake_llm_factory):
    session = make_session(fake_llm_factory(), hearing=make_hearing(fake_transcriber_factory(["Yes."])))
    await session.handle({"type": "mic_start"})
    await say(session, speech_audio, ms=300)
    await settle()
    await session.wait_idle()
    assert recorder.of("user_message")[0]["message"]["content"] == "Yes."


async def test_clicks_are_not_transcribed(make_session, make_hearing, fake_transcriber_factory, recorder, speech_audio):
    transcriber = fake_transcriber_factory()
    session = make_session(hearing=make_hearing(transcriber))
    await session.handle({"type": "mic_start"})
    for _ in range(3):
        await say(session, speech_audio, ms=100, pause=200)
    await settle()
    assert transcriber.received == []
    assert "user_speaking" not in recorder.types()
