import json

import httpx
import pytest

from digital_me.llm import LLMError, OllamaClient
from digital_me.llm.ollama import _error_text


def ndjson(*objects):
    return "\n".join(json.dumps(o) for o in objects) + "\n"


def client_with(handler):
    return OllamaClient("http://127.0.0.1:11434", "m", transport=httpx.MockTransport(handler))


async def drain(client, **kwargs):
    return [c async for c in client.stream_chat([{"role": "user", "content": "hi"}], **kwargs)]


async def test_request_payload_shape():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, text=ndjson({"message": {"content": "x"}, "done": True}))

    await drain(client_with(handler), temperature=0.3, num_ctx=2048)
    assert seen["path"] == "/api/chat"
    body = seen["body"]
    assert body["model"] == "m" and body["stream"] is True and body["keep_alive"] == "30m"
    assert body["options"] == {"temperature": 0.3, "num_ctx": 2048}


async def test_blank_lines_and_empty_content_skipped():
    text = "\n" + ndjson({"message": {"content": ""}}, {"message": {}}, {"message": {"content": "a"}}, {"done": True})
    chunks = await drain(client_with(lambda r: httpx.Response(200, text=text)))
    assert chunks == ["a"]


async def test_stops_at_done_even_if_more_lines_follow():
    text = ndjson({"message": {"content": "a"}, "done": True}, {"message": {"content": "ignored"}})
    assert await drain(client_with(lambda r: httpx.Response(200, text=text))) == ["a"]


async def test_malformed_json_line():
    with pytest.raises(LLMError, match="Malformed"):
        await drain(client_with(lambda r: httpx.Response(200, text="not json\n")))


async def test_error_object_in_stream():
    text = ndjson({"error": "model crashed"})
    with pytest.raises(LLMError, match="model crashed"):
        await drain(client_with(lambda r: httpx.Response(200, text=text)))


async def test_timeout_mapped():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LLMError, match="too long"):
        await drain(client_with(handler))


async def test_other_transport_error_mapped():
    def handler(request):
        raise httpx.RemoteProtocolError("bad", request=request)

    with pytest.raises(LLMError, match="request failed"):
        await drain(client_with(handler))


def flaky(responses):
    """Transport returning the given responses (or raising exceptions) in order."""
    calls = []

    def handler(request):
        item = responses[len(calls)]
        calls.append(request)
        if isinstance(item, Exception):
            raise item
        return item

    return OllamaClient("http://127.0.0.1:11434", "m", transport=httpx.MockTransport(handler), retry_delay=0), calls


OK_STREAM = ndjson({"message": {"content": "hi"}, "done": True})


async def test_retries_once_after_server_error():
    client, calls = flaky([httpx.Response(500, json={"error": "runner crashed"}), httpx.Response(200, text=OK_STREAM)])
    assert await drain(client) == ["hi"]
    assert len(calls) == 2


async def test_retries_once_after_dropped_connection():
    client, calls = flaky([httpx.RemoteProtocolError("dropped"), httpx.Response(200, text=OK_STREAM)])
    assert await drain(client) == ["hi"]
    assert len(calls) == 2


async def test_gives_up_after_one_retry():
    client, calls = flaky([httpx.Response(500, text="x"), httpx.Response(503, text="y")])
    with pytest.raises(LLMError, match="503"):
        await drain(client)
    assert len(calls) == 2


async def test_client_errors_are_not_retried():
    client, calls = flaky([httpx.Response(404, json={"error": "no model"})])
    with pytest.raises(LLMError, match="no model"):
        await drain(client)
    assert len(calls) == 1


async def test_unreachable_server_is_not_retried():
    client, calls = flaky([httpx.ConnectError("refused")])
    with pytest.raises(LLMError, match="Is Ollama running"):
        await drain(client)
    assert len(calls) == 1


async def test_no_retry_once_text_was_streamed():
    class DropAfterFirstChunk(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield (json.dumps({"message": {"content": "par"}}) + "\n").encode()
            raise httpx.ReadError("connection lost")

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=DropAfterFirstChunk())

    client = OllamaClient("http://127.0.0.1:11434", "m", transport=httpx.MockTransport(handler), retry_delay=0)
    received = []
    with pytest.raises(LLMError):
        async for chunk in client.stream_chat([{"role": "user", "content": "hi"}]):
            received.append(chunk)
    assert received == ["par"]  # a retry would repeat text the user already saw
    assert len(calls) == 1


def test_error_text_variants():
    assert _error_text(b'{"error": "nope"}') == "nope"
    assert _error_text(b"plain") == "plain"
    assert _error_text(b"[1,2]") == "[1,2]"


async def test_health_matches_latest_suffix():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "m:latest"}]})

    health = await client_with(handler).health()
    assert health.reachable and health.model_available


async def test_health_invalid_json():
    health = await client_with(lambda r: httpx.Response(200, text="<html>")).health()
    assert health.reachable is False
