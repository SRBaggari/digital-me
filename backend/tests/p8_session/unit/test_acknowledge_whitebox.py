import base64
import io
import wave

import numpy as np

from digital_me.server.speech import ACK_TEXT, Acknowledger, trim_silence


def test_trim_silence_keeps_a_little_padding():
    audio = np.concatenate([np.zeros(1000), np.full(200, 0.5), np.zeros(5000)]).astype(np.float32)
    trimmed = trim_silence(audio, 1000, keep_s=0.05)
    assert len(trimmed) == 200 + 2 * 50


def test_trim_silence_of_silence_is_empty():
    assert len(trim_silence(np.zeros(500, dtype=np.float32), 1000)) == 0


def test_acknowledgement_generated_once_per_voice_and_speed(fake_tts_factory):
    tts = fake_tts_factory()
    ack = Acknowledger(tts)
    first = ack.event("v1", 1.0)
    assert ack.event("v1", 1.0) is first
    ack.event("v2", 1.0)
    ack.event("v1", 1.3)
    assert [c[0] for c in tts.calls] == [ACK_TEXT] * 3


def test_acknowledgement_event_is_playable_and_unlabelled(fake_tts_factory):
    event = Acknowledger(fake_tts_factory()).event("v1", 1.0)
    assert event["type"] == "audio" and event["ack"] is True
    assert event["text"] == "" and event["words"] == []
    with wave.open(io.BytesIO(base64.b64decode(event["data"]))) as wav:
        assert wav.getnframes() > 0


async def test_warm_up_pregenerates_acknowledgement(make_context, make_speech):
    from digital_me.server.app import _warm_up_speech

    context = make_context()
    context.speech = make_speech()
    await _warm_up_speech(context)
    assert (context.speech.preferences.get().voice, 1.0) in context.speech.acknowledger._cache


async def test_ignored_utterance_is_not_acknowledged(make_session, make_hearing, make_speech, speech_audio, recorder, fake_llm_factory):
    import asyncio

    session = make_session(fake_llm_factory(), make_speech(), make_hearing(barge_in=False))
    await session.handle({"type": "mic_start"})
    await session.handle({"type": "playback", "playing": True})  # its own voice is playing
    await session.handle_audio(speech_audio.voice(700) + speech_audio.silence(700))
    await asyncio.sleep(0.05)
    assert not any(a.get("ack") for a in recorder.of("audio"))
