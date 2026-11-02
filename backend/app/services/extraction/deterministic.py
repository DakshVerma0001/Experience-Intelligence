"""
Deterministic (non-AI) extraction for fields where regex/rules are more
reliable than an LLM: email, telephone, currency, dates, assignment number,
and obvious "Label: Value" style fields. Used as the first extraction pass;
only ambiguous/semantic fields are handed to the LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?:[\s.-]?\d{2,4})?"
)
_CURRENCY_RE = re.compile(
    r"(?:Rs\.?|₹|INR|Rupees)?\s*([\d.,]+(?:\s*[.,]\s*\d+)?)\s*(crore|crores|lakh|lakhs|c\s*ore|c\s*rore)?",
    re.IGNORECASE,
)
_ASSIGNMENT_RE = re.compile(r"assignment\s*[-#:]?\s*(\d+)", re.IGNORECASE)

_MONTH_YEAR_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
    re.IGNORECASE,
)
_NUMERIC_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{4})\b")
_YEAR_ONLY_RE = re.compile(r"\b(19|20)\d{2}\b")
_ONGOING_RE = re.compile(r"\bongoing\b", re.IGNORECASE)


@dataclass
class DeterministicHit:
    field: str
    value: str
    source_text: str
    extraction_type: str = "explicit"
    confidence: float = 0.95


def extract_emails(text: str) -> list[str]:
    return list(dict.fromkeys(_EMAIL_RE.findall(text)))


def extract_currency_mentions(text: str) -> list[tuple[str, str | None, str]]:
    """Returns list of (raw_number, unit, original_matched_text). Only returns
    matches that had an explicit currency cue (Rs./₹/crore/lakh) to avoid
    false positives on arbitrary numbers."""
    hits = []
    for m in _CURRENCY_RE.finditer(text):
        raw_number, unit = m.group(1), m.group(2)
        full = m.group(0).strip()
        has_cue = bool(unit) or "rs" in full.lower() or "₹" in full or "inr" in full.lower() or "rupees" in full.lower()
        if raw_number and has_cue:
            hits.append((raw_number, unit, full))
    return hits


def extract_assignment_number(text: str) -> str | None:
    m = _ASSIGNMENT_RE.search(text)
    return f"Assignment-{m.group(1)}" if m else None


def extract_dates(text: str) -> list[str]:
    """Returns raw date-like substrings found in text, preserving whatever
    precision the source actually contains (never fabricating a day)."""
    found = []
    found += [f"{m.group(1)} {m.group(2)}" for m in _MONTH_YEAR_RE.finditer(text)]
    found += [f"{m.group(1)}/{m.group(2)}" for m in _NUMERIC_DATE_RE.finditer(text)]
    if _ONGOING_RE.search(text):
        found.append("Ongoing")
    if not found:
        found += [m.group(0) for m in _YEAR_ONLY_RE.finditer(text)]
    return found


# Canonical field -> label variants seen across old/new document templates.
LABEL_VARIANTS: dict[str, list[str]] = {
    "project_name": [
        r"name\s+of\s+(the\s+)?project",
        r"assignment\s*/\s*job\s*name",
        r"job\s*name",
    ],
    "client_name": [
        r"name\s+of\s+client(\s+and\s+address)?",
        r"name\s+and\s+address\s+of\s+client",
        r"name\s+of\s+employer",
        r"employer",
    ],
    "client_address": [r"address(\s+of\s+client)?"],
    "contact_person": [
        r"name\s+(and\s+telephone\s+no\.?\s+)?of\s+client'?s\s+representative",
        r"contact\s+person",
    ],
    "telephone": [r"telephone(\s+no\.?)?", r"tel\.?\s*no\.?", r"phone"],
    "email": [r"e-?mail"],
    "start_date": [r"start\s+date", r"date\s+started"],
    "completion_date": [r"finish\s+date", r"completion\s+date", r"date\s+completed"],
    "duration": [r"duration(\s+of\s+assignment)?(\s*/\s*job)?"],
    "contract_value": [
        r"approx\.?\s+value\s+of\s+(the\s+)?contract",
        r"estimated\s+capital\s+cost\s+of\s+the\s+project",
        r"completed\s+value\s+of\s+the\s+contract",
    ],
    "total_staff_months": [r"total\s+(no\.?\s+of\s+)?staff[\s-]months"],
    "country": [r"country(\s*&\s*location)?"],
    "applicant_name": [r"name\s+of\s+applicant", r"firm'?s\s+name"],
    "actual_services": [
        r"description\s+of\s+services\s+performed\s+by\s+the\s+applicant\s+firm",
        r"description\s+of\s+actual\s+services",
    ],
    "project_description": [
        r"brief\s+description\s+of\s+the\s+project",
        r"description\s+of\s+(the\s+)?project",
    ],
}


def extract_labeled_fields(lines: list[str]) -> dict[str, tuple[str, str]]:
    """Scans label:value style lines (and label-on-own-line, value-on-next-line
    pairs) for known field labels. Returns field -> (value, source_text)."""
    compiled = {
        field_name: [re.compile(rf"^\s*{p}\s*[:\-]?\s*", re.IGNORECASE) for p in patterns]
        for field_name, patterns in LABEL_VARIANTS.items()
    }
    results: dict[str, tuple[str, str]] = {}

    for i, line in enumerate(lines):
        for field_name, patterns in compiled.items():
            if field_name in results:
                continue
            for pattern in patterns:
                m = pattern.match(line)
                if not m:
                    continue
                value = line[m.end():].strip(" :-\t")
                if not value and i + 1 < len(lines):
                    # Label alone on its own line; value is the next line.
                    value = lines[i + 1].strip()
                    source = f"{line}\n{lines[i + 1]}"
                else:
                    source = line
                if value:
                    results[field_name] = (value, source)
                break
    return results
