from digital_me import romanised_telugu as rt
from digital_me.language import ROMANISED_TELUGU_WORDS, is_romanised_telugu


def test_unknown_words_are_transliterated_with_casual_fixes():
    assert rt._transliterate_word("repu") == "రేపు"
    santosham = rt._transliterate_word("santosham")
    assert santosham.startswith("సం") and "న్" not in santosham  # n before t -> anusvara
    assert santosham.endswith("ం")  # final m -> anusvara


def test_vowel_length_follows_telugu_syllables():
    # short before a doubled consonant or a cluster, long otherwise
    assert rt._transliterate_word("pedda") == "పెద్ద"
    assert rt._transliterate_word("prema") == "ప్రేమ"
    assert rt._transliterate_word("kosam") == "కోసం"


def test_polite_command_ending_is_retroflex():
    assert rt._transliterate_word("randi") == "రండి"
    assert rt._transliterate_word("undi") == "ఉంది"  # but "is" stays dental


def test_casual_spellings_map_to_telugu_sounds():
    assert rt._transliterate_word("thammudu").startswith("త")  # th = dental త
    assert "ష" in rt._transliterate_word("ishtapadatanu")  # sh = ష


def test_double_n_is_not_turned_into_anusvara():
    assert "న్న" in rt._transliterate_word("vunnadu")


def test_z_is_read_as_j():
    assert rt._transliterate_word("zindagi").startswith("జ")


def test_dictionary_beats_english_lexicon():
    # "anna" (elder brother) is in both; the Telugu dictionary wins inside Telugu messages
    assert rt.to_telugu_script("anna") == "అన్న"


def test_english_plural_recognised():
    assert rt.is_english_word("days") and rt.is_english_word("Happy")
    assert not rt.is_english_word("kukka")


def test_short_ambiguous_words_do_not_trigger_detection():
    for word in ["e", "na", "to", "lo", "ki", "anna", "amma"]:
        assert word not in ROMANISED_TELUGU_WORDS
    assert not is_romanised_telugu("Anna and amma went to the mall")


def test_normalise_folds_common_variants():
    assert rt.normalise("chesthunaru") == rt.normalise("chestunnaru") == rt.normalise("chesthunnaaru")
    assert rt.normalise("unnav") == rt.normalise("unnavu")


def test_english_words_never_count_through_normalisation():
    # "to" normalises like the Telugu "tho"; "the", "in", "this" must not become Telugu either
    assert not is_romanised_telugu("I want to go to the shop")
    assert not is_romanised_telugu("In this, you know.")
    assert not is_romanised_telugu("And you taste the Mardis")


def test_one_word_messages_need_a_clear_telugu_word():
    assert is_romanised_telugu("bagunnava?")
    assert not is_romanised_telugu("Hello")
