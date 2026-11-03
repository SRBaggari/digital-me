"""Spec: romanised Telugu becomes Telugu script; English words, numbers and punctuation stay."""

import pytest

from digital_me.romanised_telugu import to_telugu_script


@pytest.mark.parametrize(
    "romanised, telugu",
    [
        ("ela unnavu?", "ఎలా ఉన్నావు?"),
        ("mee kukka peru enti?", "మీ కుక్క పేరు ఏంటి?"),
        ("meeku e sangeetam istam?", "మీకు ఏ సంగీతం ఇష్టం?"),
        ("Bagunnava", "బాగున్నావా"),  # capitalised
        ("ELA UNNAVU", "ఎలా ఉన్నావు"),
    ],
)
def test_common_phrases(romanised, telugu):
    assert to_telugu_script(romanised) == telugu


@pytest.mark.parametrize(
    "romanised, telugu",
    [
        ("nenu chala happy ga unnanu", "నేను చాలా happy గా ఉన్నాను"),
        ("nenu office lo unnanu", "నేను office లో ఉన్నాను"),
        ("Hi, ela unnavu? 2 days ayyindi", "Hi, ఎలా ఉన్నావు? 2 days అయ్యింది"),
    ],
)
def test_mixed_english_words_kept(romanised, telugu):
    assert to_telugu_script(romanised) == telugu


def test_empty_and_symbols_unchanged():
    assert to_telugu_script("") == ""
    assert to_telugu_script("123 !? 😊") == "123 !? 😊"
