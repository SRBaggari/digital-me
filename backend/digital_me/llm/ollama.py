"""Streaming client for a local Ollama server (https://github.com/ollama/ollama/blob/main/docs/api.md)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx

from .base import LLMError, LLMHealth

log = logging.getLogger(__name__)


class _Retryable(LLMError):
    """A server-side failure that may succeed on a second attempt."""


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        timeout: float = 120.0,
        keep_alive: str = "30m",
        transport: httpx.AsyncBaseTransport | None = None,
        retries: int = 1,
        retry_delay: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.keep_alive = keep_alive
        self.retries = retries
        self.retry_delay = retry_delay
        self._timeout = httpx.Timeout(timeout, connect=5.0)
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, timeout=self._timeout, transport=self._transport
        )

    async def stream_chat(
        self, messages: list[dict[str, str]], *, temperature: float = 0.7, num_ctx: int = 4096
    ) -> AsyncIterator[str]:
        """Stream the reply. If Ollama fails before sending any text (e.g. its model runner
        crashed while reloading, which happens on small GPUs), retry once transparently."""
        for attempt in range(self.retries + 1):
            produced = False
            try:
                async for chunk in self._stream_once(messages, temperature, num_ctx):
                    produced = True
                    yield chunk
                return
            except _Retryable as exc:
                if produced or attempt == self.retries:
                    raise LLMError(str(exc)) from exc.__cause__
                log.warning("Ollama failed before replying (%s); retrying once", exc)
                await asyncio.sleep(self.retry_delay)

    async def _stream_once(
        self, messages: list[dict[str, str]], temperature: float, num_ctx: int
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        try:
            async with self._client() as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        message = f"Ollama returned HTTP {response.status_code}: {_error_text(body)}"
                        if response.status_code >= 500:
                            raise _Retryable(message)
                        raise LLMError(message)
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise LLMError(f"Malformed response from Ollama: {line[:200]!r}") from exc
                        if "error" in data:
                            raise LLMError(f"Ollama error: {data['error']}")
                        content = (data.get("message") or {}).get("content") or ""
                        if content:
                            yield content
                        if data.get("done"):
                            return
            raise LLMError("Ollama closed the stream before finishing the reply")
        except httpx.ConnectError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.base_url}. Is Ollama running?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError("Ollama took too long to respond") from exc
        except httpx.HTTPError as exc:  # e.g. connection dropped because the runner crashed
            raise _Retryable(f"Ollama request failed: {exc}") from exc

    async def health(self) -> LLMHealth:
        try:
            async with self._client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
                names = {m.get("name", "") for m in response.json().get("models", [])}
        except (httpx.HTTPError, ValueError) as exc:
            return LLMHealth(reachable=False, model_available=False, detail=str(exc))
        available = self.model in names or f"{self.model}:latest" in names
        detail = "" if available else f"Model {self.model!r} is not pulled. Run: ollama pull {self.model}"
        return LLMHealth(reachable=True, model_available=available, detail=detail)


def _error_text(body: bytes) -> str:
    try:
        return str(json.loads(body).get("error", body.decode(errors="replace")))
    except (ValueError, AttributeError):
        return body.decode(errors="replace")[:200]
