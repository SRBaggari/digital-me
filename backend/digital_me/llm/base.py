"""Interface every LLM backend implements."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    """The language model could not produce a response."""


@dataclass(frozen=True)
class LLMHealth:
    reachable: bool
    model_available: bool
    detail: str = ""


class LLMClient(Protocol):
    model: str

    def stream_chat(
        self, messages: list[dict[str, str]], *, temperature: float, num_ctx: int
    ) -> AsyncIterator[str]:
        """Yield the reply as text chunks. Raises LLMError on failure."""
        ...

    async def health(self) -> LLMHealth: ...
