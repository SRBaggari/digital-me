"""Spec: a profile needs a non-blank name; all other fields are optional text or text lists."""

import pytest
from pydantic import ValidationError

from digital_me.config import Profile, load_profile


def test_minimal_profile(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("name: Sam\n", encoding="utf-8")
    profile = load_profile(path)
    assert profile.name == "Sam"
    assert profile.interests == [] and profile.short_bio == ""


def test_full_profile(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text(
        "name: Sam\n"
        "short_bio: Engineer\n"
        "personality_traits: [calm, curious]\n"
        "communication_style: concise\n"
        "interests: [chess]\n"
        "background: [grew up by the sea]\n"
        "important_facts: [has a dog]\n"
        "expressions: ['honestly']\n",
        encoding="utf-8",
    )
    profile = load_profile(path)
    assert profile.personality_traits == ["calm", "curious"]
    assert profile.expressions == ["honestly"]


def test_unicode_profile(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("name: Saanvi ✨\ninterests: [संगीत]\n", encoding="utf-8")
    assert load_profile(path).interests == ["संगीत"]


def test_template_profile_is_valid(template_dir):
    assert load_profile(template_dir / "profile.yaml").name


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        Profile(name="Sam", favourite_colour="blue")


@pytest.mark.parametrize("length, ok", [(100, True), (101, False)])
def test_name_length_boundary(length, ok):
    if ok:
        assert Profile(name="a" * length)
    else:
        with pytest.raises(ValidationError):
            Profile(name="a" * length)
