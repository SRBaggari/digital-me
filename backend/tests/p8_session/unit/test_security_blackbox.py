"""Spec: only the app itself and the local dev server may open a WebSocket."""

import pytest

from digital_me.server.security import is_origin_allowed


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:8765", "http://127.0.0.1:8765", "http://localhost:5173", "http://127.0.0.1:5173"],
)
def test_local_origins_allowed(origin):
    assert is_origin_allowed(origin, 8765)


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "http://localhost.evil.example:8765",
        "http://localhost:9999",
        "https://localhost:8765",
        "http://192.168.1.4:8765",
        "null",
        "",
    ],
)
def test_foreign_origins_rejected(origin):
    assert not is_origin_allowed(origin, 8765)
