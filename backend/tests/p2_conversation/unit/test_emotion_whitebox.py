from digital_me.conversation.emotion import (
    _MAX_TAG_LENGTH,
    EmotionPart,
    EmotionTagParser,
    TextPart,
    _merge,
)


def test_incomplete_tag_is_buffered_until_closed():
    parser = EmotionTagParser()
    assert parser.feed("Hi [hap") == [TextPart("Hi ")]
    assert parser._buffer == "[hap"
    assert parser.feed("py] there") == [EmotionPart("happy"), TextPart(" there")]
    assert parser._buffer == ""


def test_overlong_open_bracket_released_as_text():
    parser = EmotionTagParser()
    text = "[" + "x" * (_MAX_TAG_LENGTH + 1)
    assert parser.feed(text) == [TextPart(text)]


def test_newline_inside_bracket_releases_it():
    parser = EmotionTagParser()
    assert parser.feed("[note\nmore") == [TextPart("[note\nmore")]


def test_overlong_closed_tag_not_treated_as_emotion():
    parser = EmotionTagParser()
    text = "[" + " " * _MAX_TAG_LENGTH + "happy]"
    assert parser.feed(text) == [TextPart(text)]


def test_newline_inside_closed_tag_not_emotion():
    parser = EmotionTagParser()
    assert parser.feed("[\nhappy]") == [TextPart("[\nhappy]")]


def test_nested_bracket_keeps_inner_tag():
    parser = EmotionTagParser()
    assert parser.feed("[[happy] ok") == [TextPart("["), EmotionPart("happy"), TextPart(" ok")]


def test_telugu_alias_becomes_emotion():
    assert EmotionTagParser().feed("[విచారంగా] సరే") == [EmotionPart("sad"), TextPart(" సరే")]


def test_unknown_telugu_tag_is_dropped():
    assert EmotionTagParser().feed("[గట్టిగా అరుస్తూ] హలో") == [TextPart(" హలో")]


def test_long_telugu_bracket_is_content():
    long_text = "[" + "అ" * 30 + "]"
    assert EmotionTagParser().feed(long_text) == [TextPart(long_text)]


def test_unknown_tag_passes_through():
    parser = EmotionTagParser()
    assert parser.feed("see [1] here") == [TextPart("see [1] here")]


def test_flush_returns_pending_buffer():
    parser = EmotionTagParser()
    parser.feed("tail [hap")
    assert parser.flush() == [TextPart("[hap")]
    assert parser.flush() == []


def test_merge_joins_only_adjacent_text():
    parts = [TextPart("a"), TextPart("b"), EmotionPart("sad"), TextPart("c")]
    assert _merge(parts) == [TextPart("ab"), EmotionPart("sad"), TextPart("c")]
