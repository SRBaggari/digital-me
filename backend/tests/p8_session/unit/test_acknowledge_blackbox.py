"""Spec: when the user stops talking, Digital Me immediately says a short "Hmm." (before the
transcript and the reply), unless acknowledgements or the voice are switched off."""

import asyncio

from digital_me.config import VoiceSettings
from digital_me.server.speech import Speech
from digital_me.tts import VoicePreferences


def speech_with(database, tts, **voice):
    return Speech(tts, VoicePreferences(database, VoiceSettings(voice="v1", **voice)))


async def talk(session, speech_audio):
    await session.handle({"type": "mic_start"})
    await session.handle_audio(speech_audio.voice(600) + speech_audio.silence(600))
    await asyncio.sleep(0.05)
    await session.wait_idle()


async def test_acknowledges_before_the_reply(make_session, make_hearing, database, fake_tts_factory, speech_audio, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(["[happy] Sure."]), speech_with(database, fake_tts_factory()), make_hearing())
    await talk(session, speech_audio)
    audio = recorder.of("audio")
    assert audio[0]["ack"] is True and audio[0]["text"] == ""  # "Hmm." comes first, without subtitles
    assert audio[1]["text"] == "Sure."
    kinds = recorder.types()
    assert kinds.index("audio") < kinds.index("transcript")  # before the words are even understood


async def test_no_acknowledgement_when_switched_off(make_session, make_hearing, database, fake_tts_factory, speech_audio, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(), speech_with(database, fake_tts_factory(), acknowledge=False), make_hearing())
    await talk(session, speech_audio)
    assert not any(a.get("ack") for a in recorder.of("audio"))


async def test_no_acknowledgement_when_voice_is_muted(make_session, make_hearing, database, fake_tts_factory, speech_audio, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(), speech_with(database, fake_tts_factory(), enabled=False), make_hearing())
    await talk(session, speech_audio)
    assert recorder.of("audio") == []


async def test_typed_messages_are_not_acknowledged(make_session, database, fake_tts_factory, recorder, fake_llm_factory):
    session = make_session(fake_llm_factory(), speech_with(database, fake_tts_factory()))
    await session.handle({"type": "user_message", "text": "hi"})
    await session.wait_idle()
    assert not any(a.get("ack") for a in recorder.of("audio"))
