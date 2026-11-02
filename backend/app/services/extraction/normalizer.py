"""
Normalizes obvious formatting problems in extracted values WITHOUT changing
their meaning. Every normalization preserves the original source text
alongside the normalized value and is tagged extraction_type="normalized".
"""
from __future__ import annotations

import re

_WS_RE = re.compile(r"\s+")


def normalize_currency_to_crore(raw_number: str, unit: str | None) -> float | None:
    """Converts a messy currency mention like 'Rs. 1. 95 c ore' into a float
    number of crores. Returns None if the number can't be parsed."""
    cleaned = _WS_RE.sub("", raw_number).replace(",", "")
    # Fix patterns like "1.95" split across whitespace already handled by _WS_RE.
    try:
        value = float(cleaned)
    except ValueError:
        return None

    unit_norm = (unit or "").lower().replace(" ", "")
    if "lakh" in unit_norm:
        return round(value / 100.0, 4)
    # Default (including "crore"/"c ore"/"crore" variants, or no unit given
    # alongside an explicit Rs./₹ cue) is treated as crore.
    return round(value, 4)


_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def normalize_date(raw: str) -> tuple[str, str]:
    """Returns (normalized_value, precision) where precision is one of
    'day' | 'month' | 'year' | 'ongoing'. Never invents a day."""
    raw_stripped = raw.strip()
    if raw_stripped.lower() == "ongoing":
        return "Ongoing", "ongoing"

    m = re.match(r"([A-Za-z]+)\s+(\d{4})", raw_stripped)
    if m and m.group(1).lower() in _MONTHS:
        return f"{m.group(2)}-{_MONTHS[m.group(1).lower()]}", "month"

    m = re.match(r"(\d{1,2})/(\d{4})", raw_stripped)
    if m:
        month = m.group(1).zfill(2)
        return f"{m.group(2)}-{month}", "month"

    m = re.match(r"^(19|20)\d{2}$", raw_stripped)
    if m:
        return raw_stripped, "year"

    return raw_stripped, "unknown"


def normalize_phone(raw: str) -> str:
    digits_and_plus = re.sub(r"[^\d+]", "", raw)
    return digits_and_plus


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


def normalize_project_status(raw: str | None) -> str:
    """Normalize into Ongoing / Completed / Cancelled / Unknown. Only infers
    from EXPLICIT wording, never merely because a completion date is missing."""
    if not raw:
        return "Unknown"
    text = raw.lower()
    if "ongoing" in text or "on-going" in text or "in progress" in text:
        return "Ongoing"
    if "cancel" in text:
        return "Cancelled"
    if "complet" in text:
        return "Completed"
    return "Unknown"


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()
