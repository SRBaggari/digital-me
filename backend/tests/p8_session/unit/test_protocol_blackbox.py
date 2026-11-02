"""Spec: exactly four client message types; unknown fields and oversize text are rejected."""

import pytest
from pydantic import ValidationError

from digital_me.server.protocol import client_message_adapter


@pytest.mark.parametrize(
    "raw",
    [
        {"type": "user_message", "text": "hello"},
        {"type": "user_message", "text": ""},
        {"type": "interrupt"},
        {"type": "new_conversation"},
        {"type": "open_conversation", "conversation_id": 3},
    ],
)
def test_valid_messages(raw):
    assert client_message_adapter.validate_python(raw).type == raw["type"]


@pytest.mark.parametrize(
    "raw",
    [
        {"type": "interrupt", "now": True},
        {"type": "user_message", "text": "a" * 20_001},
        {"type": "open_conversation"},
        {"type": "delete_everything"},
    ],
)
def test_invalid_messages(raw):
    with pytest.raises(ValidationError):
        client_message_adapter.validate_python(raw)


def test_text_length_boundary():
    assert client_message_adapter.validate_python({"type": "user_message", "text": "a" * 20_000})
