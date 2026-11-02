"""Spec: text is split into sentences at . ! ? … or newlines, never inside abbreviations
or numbers, and chunking of the input does not affect the output."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from digital_me.conversation import SentenceSplitter


def split(chunks):
    splitter = SentenceSplitter()
    out = []
    for chunk in chunks:
        out.extend(splitter.feed(chunk))
    return out + splitter.flush()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hi. How are you? Fine!", ["Hi.", "How are you?", "Fine!"]),
        ("Pi is 3.14 roughly.", ["Pi is 3.14 roughly."]),
        ("Ask Dr. Rao today. Okay.", ["Ask Dr. Rao today.", "Okay."]),
        ("Wait… what?", ["Wait…", "what?"]),
        ("No terminator", ["No terminator"]),
        ("", []),
        ("   ", []),
        ("Visit example.com now. Bye.", ["Visit example.com now.", "Bye."]),
    ],
)
def test_examples(text, expected):
    assert split([text]) == expected


def test_streamed_word_by_word():
    words = "Hello there. I am fine, thanks! And you?".split(" ")
    chunks = [w + " " for w in words]
    assert split(chunks) == ["Hello there.", "I am fine, thanks!", "And you?"]


@given(st.text(alphabet="ab .!?\n", max_size=80), st.lists(st.integers(0, 80), max_size=10))
def test_chunking_invariance(text, cut_points):
    cuts = sorted({min(c, len(text)) for c in cut_points})
    chunks = [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)], strict=True)]
    assert split(chunks) == split([text])


@given(st.text(alphabet="ab .!?\n", max_size=80))
def test_no_characters_lost(text):
    assert "".join(split([text])).replace(" ", "") == "".join(text.split())
