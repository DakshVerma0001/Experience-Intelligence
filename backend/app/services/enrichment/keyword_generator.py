from __future__ import annotations

import re

from app.ai.base import LLMProvider
from app.core.logging import get_logger
from app.services.extraction.llm_extractor import ExtractionFailedError, generate_keywords_raw

logger = get_logger(__name__)

_GENERIC_TERMS = {"project", "company", "client", "india", "work", "assignment", "firm"}


def _is_source_supported(term: str, source_text_lower: str) -> bool:
    """A keyword (or one of its word-tokens) must actually appear in the
    source text; this guards against hallucinated technologies per spec."""
    term_lower = term.lower().strip()
    if term_lower in source_text_lower:
        return True
    # Allow acronym match e.g. "GIS" already checked above; also allow a loose
    # check on the first significant word.
    tokens = [t for t in re.split(r"\W+", term_lower) if len(t) > 2]
    return any(t in source_text_lower for t in tokens) if tokens else False


def generate_keywords(provider: LLMProvider, project_text: str) -> list[dict]:
    """Returns validated keyword dicts: keyword, category, description,
    aliases, source_supported. Generic/unsupported terms are dropped rather
    than silently kept, to honor the strict data-accuracy rule."""
    try:
        raw = generate_keywords_raw(provider, project_text)
    except ExtractionFailedError as exc:
        logger.warning("Keyword generation failed: %s", exc)
        return []

    source_lower = project_text.lower()
    results: list[dict] = []
    for kw in raw.get("keywords", [])[:15]:
        keyword = (kw.get("keyword") or "").strip()
        if not keyword or keyword.lower() in _GENERIC_TERMS:
            continue
        supported = _is_source_supported(keyword, source_lower)
        if not supported:
            logger.info("Dropping unsupported keyword candidate: %s", keyword)
            continue
        aliases = [a for a in (kw.get("aliases") or []) if isinstance(a, str)]
        # Only keep aliases that are themselves plausible (appear in source or
        # are a near-substring of the keyword) - avoids hallucinated aliases.
        aliases = [a for a in aliases if a.lower() in source_lower]
        results.append(
            {
                "keyword": keyword,
                "category": kw.get("category") or "General",
                "description": kw.get("description") or "",
                "aliases": aliases,
                "source_supported": True,
            }
        )

    if len(results) > 15:
        results = results[:15]
    return results
