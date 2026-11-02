import asyncio
import base64

from digital_me.config import VoiceSettings
from digital_me.server.speech import SentenceSpeaker


async def run_speaker(tts, sentences, recorder, voice=None):
    speaker = SentenceSpeaker(tts, voice or VoiceSettings(voice="v1", speed=1.0), recorder)
    for i, text in enumerate(sentences):
        speaker.say(i, text, "happy")
    await speaker.finish()
    return speaker


async def test_sentences_synthesised_in_order(fake_tts_factory, recorder):
    tts = fake_tts_factory()
    await run_speaker(tts, ["one two.", "three."], recorder)
    assert [c[0] for c in tts.calls] == ["one two.", "three."]
    assert [e.get("index") for e in recorder.of("audio")] == [0, 1]
    assert recorder.events[-1] == {"type": "speech_end"}


async def test_voice_and_speed_from_preferences(fake_tts_factory, recorder):
    tts = fake_tts_factory()
    await run_speaker(tts, ["hi."], recorder, VoiceSettings(voice="v2", speed=1.5))
    assert tts.calls == [("hi.", "v2", 1.5)]


async def test_audio_event_payload(fake_tts_factory, recorder):
    await run_speaker(fake_tts_factory(), ["hello world"], recorder)
    [audio] = recorder.of("audio")
    assert audio["format"] == "wav" and audio["sample_rate"] == 1000
    assert audio["duration"] == 0.2
    assert base64.b64decode(audio["data"])[:4] == b"RIFF"
    assert [w["text"] for w in audio["words"]] == ["hello", "world"]
    assert audio["emotion"] == "happy" and audio["text"] == "hello world"


async def test_failure_reported_once_and_rest_skipped(fake_tts_factory, recorder):
    tts = fake_tts_factory(fail_on="bad")
    speaker = await run_speaker(tts, ["fine.", "bad one.", "later."], recorder)
    assert speaker.failed
    assert len(recorder.of("error")) == 1 and recorder.of("error")[0]["code"] == "tts_error"
    assert [c[0] for c in tts.calls] == ["fine.", "bad one."]
    assert recorder.events[-1]["type"] == "speech_end"


async def test_silent_result_sends_no_audio(fake_tts_factory, recorder):
    await run_speaker(fake_tts_factory(), [""], recorder)
    assert recorder.of("audio") == []


async def test_cancel_stops_without_speech_end(fake_tts_factory, recorder):
    speaker = SentenceSpeaker(fake_tts_factory(delay=0.2), VoiceSettings(voice="v1"), recorder)
    speaker.say(0, "slow sentence.", "neutral")
    await asyncio.sleep(0.01)
    await speaker.cancel()
    assert "speech_end" not in recorder.types()
