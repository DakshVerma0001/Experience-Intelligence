from __future__ import annotations

from app.ai.base import LLMProvider
from app.core.logging import get_logger
from app.services.extraction.llm_extractor import ExtractionFailedError, generate_search_summary_raw

logger = get_logger(__name__)


def generate_search_summary(provider: LLMProvider, project_text: str) -> str | None:
    try:
        summary = generate_search_summary_raw(provider, project_text)
    except ExtractionFailedError as exc:
        logger.warning("Search summary generation failed: %s", exc)
        return None
    if summary and isinstance(summary, str) and summary.strip():
        return summary.strip()
    return None
