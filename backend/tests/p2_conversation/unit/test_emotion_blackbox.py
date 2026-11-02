"""Spec: known emotion tags are extracted from text, everything else is preserved exactly,
and the result does not depend on how the stream is chunked."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from digital_me.conversation import EMOTIONS, EmotionTagParser, normalize_emotion
from digital_me.conversation.emotion import EmotionPart, TextPart


def parse(chunks):
    parser = EmotionTagParser()
    parts = []
    for chunk in chunks:
        parts.extend(parser.feed(chunk))
    parts.extend(parser.flush())
    text = "".join(p.text for p in parts if isinstance(p, TextPart))
    emotions = [p.emotion for p in parts if isinstance(p, EmotionPart)]
    return text, emotions


@pytest.mark.parametrize("label", EMOTIONS)
def test_every_canonical_label_recognised(label):
    assert normalize_emotion(label) == label
    assert normalize_emotion(label.upper()) == label


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("joy", "happy"),
        (" Emotion: Concerned ", "empathetic"),
        ("emotion=surprise", "surprised"),
        ("angry", None),
        ("", None),
        ("1", None),
    ],
)
def test_aliases_and_unknowns(raw, expected):
    assert normalize_emotion(raw) == expected


def test_opening_tag_extracted():
    assert parse(["[happy] Great to see you!"]) == (" Great to see you!", ["happy"])


def test_mid_reply_tag_extracted():
    assert parse(["[neutral] Okay. [sad] That is hard."]) == (" Okay.  That is hard.", ["neutral", "sad"])


def test_plain_text_untouched():
    assert parse(["No tags [here] at all, a[0] = 1"]) == ("No tags [here] at all, a[0] = 1", [])


def test_unclosed_bracket_at_end_kept():
    assert parse(["value [unfinished"]) == ("value [unfinished", [])


SEGMENTS = st.lists(
    st.one_of(
        st.sampled_from(
            [f"[{e}]" for e in EMOTIONS] + ["[Joy]", "[x]", "[", "]", "happy", " " * 20]
        ),
        st.text(alphabet="ab .,!?\n[]", max_size=12),
    ),
    max_size=12,
)


@given(SEGMENTS, st.lists(st.integers(min_value=0, max_value=200), max_size=8))
def test_chunking_does_not_change_result(segments, cut_points):
    text = "".join(segments)
    cuts = sorted({min(c, len(text)) for c in cut_points})
    chunks = [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)], strict=True)]
    assert parse(chunks) == parse([text])


@given(st.text(alphabet="abc .!?\n()", max_size=60))
def test_text_without_brackets_round_trips(text):
    assert parse([text]) == (text, [])
