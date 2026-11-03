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


@pytest.mark.parametrize(
    "variant, telugu",
    [
        ("em chesthunaru", "ఏం చేస్తున్నారు"),  # from a real conversation: was answered in English
        ("em chestunnaru", "ఏం చేస్తున్నారు"),
        ("ela unnav", "ఎలా ఉన్నావు"),
        ("thinnava", "తిన్నావా"),
        ("bagunnaaraa", "బాగున్నారా"),
        ("nuvvu ippudu ekkada unnav", "నువ్వు ఇప్పుడు ఎక్కడ ఉన్నావు"),
    ],
)
def test_spelling_variants(variant, telugu):
    from digital_me.language import detect_language

    assert detect_language(variant) == "te"
    assert to_telugu_script(variant) == telugu


@pytest.mark.parametrize(
    "romanised, telugu",
    [
        ("repu cinema ki veldama?", "రేపు సినిమా కి వెళ్దామా?"),
        ("naaku konchem aakali ga undi", "నాకు కొంచెం ఆకలి గా ఉంది"),
        ("nijamga cheppu, emaindi?", "నిజంగా చెప్పు, ఏమైంది?"),
    ],
)
def test_everyday_sentences(romanised, telugu):
    assert to_telugu_script(romanised) == telugu


def test_english_words_listed_in_the_dictionary_do_not_make_english_telugu():
    from digital_me.language import detect_language

    assert detect_language("I went to the cinema") == "en"
    assert detect_language("My friend Ela is here") == "en"


def test_empty_and_symbols_unchanged():
    assert to_telugu_script("") == ""
    assert to_telugu_script("123 !? 😊") == "123 !? 😊"
