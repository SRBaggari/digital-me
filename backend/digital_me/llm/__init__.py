"""Language-model backends (local only)."""

from .base import LLMClient, LLMError, LLMHealth
from .ollama import OllamaClient

__all__ = ["LLMClient", "LLMError", "LLMHealth", "OllamaClient"]
