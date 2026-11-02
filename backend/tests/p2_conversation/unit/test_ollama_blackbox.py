"""Spec (Ollama /api/chat streaming contract): the client yields message chunks in order and
turns every failure into LLMError with a human-readable explanation."""

import json

import httpx
import pytest

from digital_me.llm import LLMError, OllamaClient


def server(handler):
    return OllamaClient("http://127.0.0.1:11434", "llama3.2:3b", transport=httpx.MockTransport(handler))


async def drain(client):
    return [c async for c in client.stream_chat([{"role": "user", "content": "hi"}])]


async def test_streams_chunks_in_order():
    lines = [{"message": {"role": "assistant", "content": w}, "done": False} for w in ["Hel", "lo", "!"]]
    lines.append({"message": {"role": "assistant", "content": ""}, "done": True})
    body = "\n".join(json.dumps(line) for line in lines)
    assert await drain(server(lambda r: httpx.Response(200, text=body))) == ["Hel", "lo", "!"]


async def test_recovers_transparently_when_the_model_runner_crashes_once():
    replies = iter(
        [
            httpx.Response(500, json={"error": "llama runner process has terminated"}),
            httpx.Response(200, text=json.dumps({"message": {"content": "Hello!"}, "done": True})),
        ]
    )
    client = OllamaClient(
        "http://127.0.0.1:11434", "llama3.2:3b", transport=httpx.MockTransport(lambda r: next(replies)), retry_delay=0
    )
    assert await drain(client) == ["Hello!"]


async def test_http_error_status():
    client = server(lambda r: httpx.Response(404, json={"error": "model 'x' not found"}))
    with pytest.raises(LLMError, match="404.*not found"):
        await drain(client)


async def test_unreachable_server():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMError, match="Is Ollama running"):
        await drain(server(handler))


async def test_stream_ends_without_done():
    body = json.dumps({"message": {"content": "half"}})
    with pytest.raises(LLMError, match="before finishing"):
        await drain(server(lambda r: httpx.Response(200, text=body)))


async def test_health_reports_missing_model():
    client = server(lambda r: httpx.Response(200, json={"models": [{"name": "other:1b"}]}))
    health = await client.health()
    assert health.reachable and not health.model_available
    assert "ollama pull llama3.2:3b" in health.detail


async def test_health_unreachable():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    health = await server(handler).health()
    assert not health.reachable and not health.model_available
