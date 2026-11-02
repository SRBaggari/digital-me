import asyncio
import base64

from digital_me.config import VoiceSettings
from digital_me.server.speech import SentenceSpeaker, speakable_chunks


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


def test_first_chunk_uses_tighter_limit():
    text = "Well, to be honest, I think that rock climbing is the best thing in the world."
    assert speakable_chunks(text, first=True) == [
        "Well, to be honest,",  # "Well," alone is too short to stand as a clip
        "I think that rock climbing is the best thing in the world.",
    ]
    assert speakable_chunks(text, first=False) == [text]  # 15 words: under the normal limit


def test_no_tiny_trailing_fragment():
    text = "I spent the whole afternoon climbing up at the crag, okay?"
    assert speakable_chunks(text, first=True) == [text]


def test_first_clause_too_short_is_extended_to_next_boundary():
    text = "Yes, the cat, Miso, sleeps in the sun all day long and chases flies."
    assert speakable_chunks(text, first=True)[0] == "Yes, the cat,"


async def test_clips_numbered_across_split_sentences(fake_tts_factory, recorder):
    speaker = SentenceSpeaker(fake_tts_factory(), VoiceSettings(voice="v1"), recorder)
    speaker.say(0, "Honestly, my favourite thing, without a doubt, is reading in the park on a slow weekend.", "neutral")
    speaker.say(1, "Short one.", "neutral")
    await speaker.finish()
    audio = recorder.of("audio")
    assert [a["index"] for a in audio] == [0, 1, 2]
    assert [a["text"] for a in audio] == [
        "Honestly, my favourite thing,",
        "without a doubt, is reading in the park on a slow weekend.",
        "Short one.",
    ]


async def test_cancel_stops_without_speech_end(fake_tts_factory, recorder):
    speaker = SentenceSpeaker(fake_tts_factory(delay=0.2), VoiceSettings(voice="v1"), recorder)
    speaker.say(0, "slow sentence.", "neutral")
    await asyncio.sleep(0.01)
    await speaker.cancel()
    assert "speech_end" not in recorder.types()
