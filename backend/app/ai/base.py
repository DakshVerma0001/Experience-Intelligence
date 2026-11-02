from __future__ import annotations

from dataclasses import dataclass


class LLMUnavailableError(Exception):
    """Raised when the local LLM provider cannot be reached or the configured
    model is not installed. Never falls back to a paid/external API."""


@dataclass
class LLMResponse:
    raw_text: str
    model: str


class LLMProvider:
    """Abstract local LLM provider. Implementations must never send data to
    an external network service other than the local inference server."""

    def is_available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def generate(self, prompt: str, *, temperature: float = 0.1) -> LLMResponse:
        raise NotImplementedError
