from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from app.ai.base import LLMProvider, LLMUnavailableError
from app.core.logging import get_logger
from app.schemas.extraction import LLMExtractionResult

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "ai" / "prompts"

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    # Strip markdown code fences if the model added them despite instructions.
    text = re.sub(r"^```(json)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    match = _JSON_BLOCK_RE.search(text)
    candidate = match.group(0) if match else text
    return json.loads(candidate)


class ExtractionFailedError(Exception):
    pass


def extract_project_fields(provider: LLMProvider, segment_text: str) -> LLMExtractionResult:
    """Runs the project_extraction prompt, validates the JSON output against
    LLMExtractionResult, and retries once with a correction prompt on failure.
    Never inserts malformed AI output - raises ExtractionFailedError instead."""
    template = _load_prompt("project_extraction.txt")
    prompt = template.replace("{{SEGMENT_TEXT}}", segment_text)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = provider.generate(prompt)
            data = _extract_json(response.raw_text)
            return LLMExtractionResult.model_validate(data)
        except LLMUnavailableError:
            raise
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning("LLM extraction attempt %s failed validation: %s", attempt + 1, exc)
            prompt = (
                template.replace("{{SEGMENT_TEXT}}", segment_text)
                + f"\n\nYour previous response was invalid JSON or did not match the schema "
                f"({exc}). Return ONLY a valid JSON object matching the schema exactly."
            )

    raise ExtractionFailedError(f"LLM extraction failed after retries: {last_error}")


def generate_keywords_raw(provider: LLMProvider, project_text: str) -> dict:
    template = _load_prompt("keyword_generation.txt")
    prompt = template.replace("{{PROJECT_TEXT}}", project_text)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = provider.generate(prompt)
            return _extract_json(response.raw_text)
        except LLMUnavailableError:
            raise
        except json.JSONDecodeError as exc:
            last_error = exc
            prompt = prompt + f"\n\nYour previous response was invalid JSON ({exc}). Return ONLY valid JSON."
    raise ExtractionFailedError(f"Keyword generation failed after retries: {last_error}")


def generate_search_summary_raw(provider: LLMProvider, project_text: str) -> str | None:
    template = _load_prompt("search_summary.txt")
    prompt = template.replace("{{PROJECT_TEXT}}", project_text)
    for attempt in range(2):
        try:
            response = provider.generate(prompt)
            data = _extract_json(response.raw_text)
            return data.get("summary")
        except LLMUnavailableError:
            raise
        except json.JSONDecodeError as exc:
            prompt = prompt + f"\n\nYour previous response was invalid JSON ({exc}). Return ONLY valid JSON."
    return None
