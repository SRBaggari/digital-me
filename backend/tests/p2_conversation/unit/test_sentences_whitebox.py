import pytest

from digital_me.conversation.sentences import SentenceSplitter, _is_abbreviation


def test_terminator_at_end_waits_for_next_char():
    splitter = SentenceSplitter()
    assert splitter.feed("Hello.") == []
    assert splitter.pending == "Hello."
    assert splitter.feed(" Next") == ["Hello."]
    assert splitter.pending == " Next"


def test_closing_quote_stays_with_sentence():
    splitter = SentenceSplitter()
    assert splitter.feed('She said "hi." Then') == ['She said "hi."']


def test_multiple_terminators_grouped():
    splitter = SentenceSplitter()
    assert splitter.feed("Really?! Yes") == ["Really?!"]


def test_newline_is_boundary():
    splitter = SentenceSplitter()
    assert splitter.feed("Line one\nLine two") == ["Line one"]


def test_whitespace_only_segments_dropped():
    splitter = SentenceSplitter()
    assert splitter.feed("\n\n  \nWord. ") == ["Word."]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Dr.", True),
        ("see e.g.", True),
        ("J.", True),
        ("I.", False),
        ("word.", False),
        ("3.", False),
    ],
)
def test_is_abbreviation(text, expected):
    assert _is_abbreviation(text, len(text) - 1) is expected


def test_flush_clears_buffer():
    splitter = SentenceSplitter()
    splitter.feed("unfinished thought")
    assert splitter.flush() == ["unfinished thought"]
    assert splitter.flush() == []
