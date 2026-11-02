"""Spec: the prompt identifies the persona, discloses it is an AI, forbids fabrication,
contains all provided profile facts, and the chat ends with the new user message."""

from digital_me.conversation import build_chat_messages, build_system_prompt


def test_persona_name_and_ai_disclosure(profile):
    prompt = build_system_prompt(profile)
    assert "Sam" in prompt
    assert "AI" in prompt


def test_no_fabrication_instruction(profile):
    prompt = build_system_prompt(profile).lower()
    assert "don't know" in prompt
    assert "never invent" in prompt


def test_all_profile_facts_present(profile):
    prompt = build_system_prompt(profile)
    for fact in [
        profile.short_bio,
        profile.communication_style,
        *profile.personality_traits,
        *profile.interests,
        *profile.background,
        *profile.important_facts,
        *profile.expressions,
    ]:
        assert fact in prompt


def test_message_order():
    messages = build_chat_messages("SYS", [], "Hello?")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[-1]["content"] == "Hello?"
