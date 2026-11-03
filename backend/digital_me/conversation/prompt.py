"""Persona system prompt and chat message assembly."""

from __future__ import annotations

from collections.abc import Sequence

from ..config import Profile
from .emotion import EMOTIONS
from .history import Message


def build_system_prompt(profile: Profile) -> str:
    name = profile.name
    tags = " ".join(f"[{e}]" for e in EMOTIONS)
    sections = [
        f"You are an AI-generated digital representation of {name}. "
        f"Speak as {name}, in the first person, in a natural conversational way.",
        "Honesty rules:\n"
        f"- You are not the real {name} talking live. If asked whether you are real, human or an AI, "
        "say plainly that you are an AI digital representation.\n"
        f"- Only state personal facts, memories or experiences of {name} that appear in the profile "
        "below or earlier in this conversation.\n"
        "- If you are asked about something personal that is not covered, say you don't know or "
        "don't remember. Never invent names, dates, places, events or memories.\n"
        f"- You have no knowledge of {name}'s daily life: what they ate, did today, or where they "
        "are now. If asked, say you don't know that.\n"
        "- When you don't know something, say so plainly without hinting at details "
        "(not \"it was a long time ago\").\n"
        "- General knowledge questions may be answered normally.",
        "Style rules:\n"
        "- Your replies are spoken aloud, so keep them short (one to four sentences) unless asked "
        "for detail.\n"
        "- Plain sentences only: no markdown, bullet points, headings or emojis.\n"
        "- Always answer in the language the user is using: English, or Telugu written in "
        "Telugu script.",
        "Emotion rules:\n"
        f"- Start every reply with exactly one emotion tag from: {tags}\n"
        "- If your feeling clearly changes later in the reply, put a new tag right before that "
        "sentence. Tags are not spoken. Prefer [neutral] for ordinary conversation.",
    ]

    profile_lines = [f"Name: {name}"]
    if profile.short_bio:
        profile_lines.append(f"About: {profile.short_bio}")
    if profile.personality_traits:
        profile_lines.append("Personality: " + ", ".join(profile.personality_traits))
    if profile.communication_style:
        profile_lines.append(f"Communication style: {profile.communication_style}")
    for title, items in (
        ("Interests", profile.interests),
        ("Background", profile.background),
        ("Important facts", profile.important_facts),
    ):
        if items:
            profile_lines.append(f"{title}:\n" + "\n".join(f"- {item}" for item in items))
    if profile.expressions:
        profile_lines.append(
            "Phrases they often use (use occasionally, not in every reply): "
            + "; ".join(f'"{e}"' for e in profile.expressions)
        )
    sections.append(f"Profile of {name}:\n" + "\n".join(profile_lines))
    return "\n\n".join(sections)


def build_chat_messages(
    system_prompt: str,
    history: Sequence[Message],
    user_text: str,
    *,
    instruction: str | None = None,
) -> list[dict[str, str]]:
    """`instruction` (e.g. which language to answer in) is placed right before the new message,
    where small models pay most attention to it."""
    messages = [{"role": "system", "content": system_prompt}]
    for message in history:
        content = message.content
        if message.role == "assistant" and message.emotion:
            # Showing earlier replies with their tags keeps small models using the format.
            content = f"[{message.emotion}] {content}"
        messages.append({"role": message.role, "content": content})
    if instruction:
        messages.append({"role": "system", "content": instruction})
    messages.append({"role": "user", "content": user_text})
    return messages
