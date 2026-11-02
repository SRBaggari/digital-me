from digital_me.config import Profile
from digital_me.conversation import EMOTIONS, build_chat_messages, build_system_prompt
from digital_me.conversation.history import Message


def msg(role, content, emotion=None):
    return Message(1, 1, role, content, emotion, False, "t")


def test_empty_optional_sections_omitted():
    prompt = build_system_prompt(Profile(name="Sam"))
    for heading in ("About:", "Personality:", "Interests:", "Background:", "Important facts:", "Phrases"):
        assert heading not in prompt


def test_every_emotion_tag_listed():
    prompt = build_system_prompt(Profile(name="Sam"))
    for emotion in EMOTIONS:
        assert f"[{emotion}]" in prompt


def test_list_items_rendered_as_bullets(profile):
    prompt = build_system_prompt(profile)
    assert "Interests:\n- chess\n- hiking" in prompt
    assert '"to be honest"' in prompt


def test_assistant_history_gets_emotion_prefix():
    messages = build_chat_messages(
        "SYS", [msg("user", "hi"), msg("assistant", "hello", "happy"), msg("assistant", "plain")], "next"
    )
    assert messages[0] == {"role": "system", "content": "SYS"}
    assert messages[2]["content"] == "[happy] hello"
    assert messages[3]["content"] == "plain"


def test_user_history_never_prefixed():
    messages = build_chat_messages("SYS", [msg("user", "hi", "sad")], "next")
    assert messages[1]["content"] == "hi"
