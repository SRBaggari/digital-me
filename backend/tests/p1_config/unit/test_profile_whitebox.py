import pytest

from digital_me.config.profile import Profile, ProfileError, load_profile


def test_list_validator_none_becomes_empty():
    assert Profile(name="A", interests=None).interests == []


def test_list_validator_rejects_non_list():
    with pytest.raises(ValueError, match="list"):
        Profile(name="A", interests="hiking")


def test_list_validator_rejects_nested_structures():
    with pytest.raises(ValueError, match="text"):
        Profile(name="A", interests=[{"a": 1}])


def test_list_validator_coerces_numbers_and_drops_blanks():
    assert Profile(name="A", important_facts=[1990, "  ", " tall "]).important_facts == [
        "1990",
        "tall",
    ]


def test_name_is_stripped_and_blank_rejected():
    assert Profile(name="  Sam  ").name == "Sam"
    with pytest.raises(ValueError):
        Profile(name="   ")


def test_load_profile_wraps_yaml_errors(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("name: [unclosed", encoding="utf-8")
    with pytest.raises(ProfileError, match="not valid YAML"):
        load_profile(path)


def test_load_profile_requires_mapping(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="mapping"):
        load_profile(path)


def test_load_profile_wraps_validation_errors(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("short_bio: no name\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="Invalid profile"):
        load_profile(path)


def test_load_profile_missing_file(tmp_path):
    with pytest.raises(ProfileError, match="not found"):
        load_profile(tmp_path / "missing.yaml")
