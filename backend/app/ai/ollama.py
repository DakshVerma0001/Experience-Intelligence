from __future__ import annotations

import httpx

from app.ai.base import LLMProvider, LLMResponse, LLMUnavailableError
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout_seconds

    def is_available(self) -> tuple[bool, str]:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception:
            return False, "Ollama is not running."
        try:
            tags = resp.json().get("models", [])
            names = [t.get("name", "").split(":")[0] for t in tags]
            if self.model.split(":")[0] not in names:
                return False, f"Configured model '{self.model}' is unavailable. Run: ollama pull {self.model}"
        except Exception:
            return False, "Ollama returned an unexpected response."
        return True, "Ollama is running and the configured model is installed."

    def generate(self, prompt: str, *, temperature: float = 0.1) -> LLMResponse:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMUnavailableError("Ollama is not running.") from exc
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError(
                f"Ollama request timed out after {self.timeout}s. The model may be too slow for this "
                "hardware/document on CPU, or the document segment too large. Try increasing "
                "OLLAMA_TIMEOUT_SECONDS in backend/.env, or use a smaller/faster model."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMUnavailableError(f"Ollama request failed: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailableError(f"Ollama request failed: {exc}") from exc

        data = resp.json()
        return LLMResponse(raw_text=data.get("response", ""), model=self.model)
