from digital_me.conversation.history import Conversation, Message
from digital_me.server.protocol import (
    STATES,
    UserMessage,
    client_message_adapter,
    conversation_to_dict,
    error_event,
    message_to_dict,
)
from digital_me.server.session import _first_error


def test_discriminator_selects_model():
    parsed = client_message_adapter.validate_python({"type": "user_message", "text": "hi"})
    assert isinstance(parsed, UserMessage)


def test_message_serialisation_has_all_fields():
    message = Message(1, 2, "assistant", "hi", "happy", True, "t")
    assert message_to_dict(message) == {
        "id": 1,
        "conversation_id": 2,
        "role": "assistant",
        "content": "hi",
        "emotion": "happy",
        "interrupted": True,
        "created_at": "t",
    }


def test_conversation_serialisation():
    assert conversation_to_dict(Conversation(1, "t", None, 0))["message_count"] == 0


def test_error_event_shape():
    assert error_event("x", "y") == {"type": "error", "code": "x", "detail": "y"}


def test_first_error_includes_location():
    try:
        client_message_adapter.validate_python({"type": "user_message", "text": 1})
    except Exception as exc:
        assert "text" in _first_error(exc)


def test_states_cover_ui_indicators():
    assert set(STATES) == {"idle", "listening", "thinking", "speaking"}
