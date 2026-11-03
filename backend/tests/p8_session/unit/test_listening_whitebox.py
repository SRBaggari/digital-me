import asyncio

import numpy as np

from digital_me.server.listener import Listener, pcm16_to_float
from digital_me.stt import STTError, SpeechDetector


def test_pcm16_decoding_and_odd_byte_tolerance():
    data = np.array([0, 16384, -32768], dtype="<i2").tobytes() + b"\x01"
    assert pcm16_to_float(data).tolist() == [0.0, 0.5, -1.0]


async def make_listener(transcriber, speech_audio, recorder, on_transcript=None):
    heard = []

    async def transcript(text, language=None):
        heard.append(text)

    async def started():
        pass

    listener = Listener(
        SpeechDetector(speech_audio.vad()),
        transcriber,
        on_speech_start=started,
        on_transcript=on_transcript or transcript,
        send=recorder,
    )
    return listener, heard


async def test_transcripts_delivered_in_speaking_order(fake_transcriber_factory, speech_audio, recorder):
    transcriber = fake_transcriber_factory(["first", "second"], delay=0.05)
    listener, heard = await make_listener(transcriber, speech_audio, recorder)
    for _ in range(2):
        await listener.feed(speech_audio.voice(500))
        await listener.feed(speech_audio.silence(800))
    await asyncio.sleep(0.3)
    assert heard == ["first", "second"]
    await listener.close()


async def test_transcription_error_reported_and_listening_continues(fake_transcriber_factory, speech_audio, recorder):
    broken = fake_transcriber_factory(error=STTError("model missing"))
    listener, heard = await make_listener(broken, speech_audio, recorder)
    await listener.feed(speech_audio.voice(500) + speech_audio.silence(800))
    await asyncio.sleep(0.05)
    assert recorder.of("error")[0]["code"] == "stt_error"
    assert recorder.of("transcript") == [{"type": "transcript", "text": ""}]
    broken.error = None
    await listener.feed(speech_audio.voice(500) + speech_audio.silence(800))
    await asyncio.sleep(0.05)
    assert heard == ["hello there"]
    await listener.close()


async def test_playback_flag_reaches_detector(fake_transcriber_factory, speech_audio, recorder):
    listener, _ = await make_listener(fake_transcriber_factory(), speech_audio, recorder)
    listener.playback = True
    assert listener._detector.playback is True
    await listener.close()


async def test_session_passes_playback_state_to_new_listener(make_session, make_hearing):
    session = make_session(hearing=make_hearing())
    await session.handle({"type": "playback", "playing": True})
    await session.handle({"type": "mic_start"})
    assert session._listener.playback is True
    await session.handle({"type": "playback", "playing": False})
    assert session._listener.playback is False
    await session.close()


async def test_restarting_mic_replaces_listener(make_session, make_hearing):
    session = make_session(hearing=make_hearing())
    await session.handle({"type": "mic_start"})
    first = session._listener
    await session.handle({"type": "mic_start"})
    assert session._listener is not first
    assert first._worker.done()
    await session.close()
    assert session._listener is None


async def test_ignore_flag_cleared_after_dropped_utterance(make_session, make_hearing, speech_audio, fake_llm_factory, recorder):
    session = make_session(fake_llm_factory(), hearing=make_hearing(barge_in=False))
    await session.handle({"type": "mic_start"})
    await session.handle({"type": "playback", "playing": True})
    await session.handle_audio(speech_audio.voice(700) + speech_audio.silence(800))
    await asyncio.sleep(0.05)
    assert session._ignore_utterance is False
    await session.handle({"type": "playback", "playing": False})
    await session.handle_audio(speech_audio.voice(500) + speech_audio.silence(800))
    await asyncio.sleep(0.05)
    await session.wait_idle()
    assert len(recorder.of("user_message")) == 1  # the second one, said after the reply ended
