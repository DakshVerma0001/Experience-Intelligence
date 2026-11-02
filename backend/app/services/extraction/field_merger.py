"""
Merges deterministic (regex/rule-based) extraction with LLM semantic
extraction into the canonical project field set, building field-level
provenance records for every important field. Deterministic values win for
fields they cover (email, phone, currency, dates, assignment number);
LLM values fill in the semantic fields deterministic extraction can't reach.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from app.schemas.extraction import LLMExtractionResult
from app.services.extraction import deterministic, normalizer


@dataclass
class MergedField:
    value: str | None
    source_text: str | None
    source_location: str | None
    confidence: float | None
    extraction_type: str | None  # explicit | derived | normalized


@dataclass
class MergedProject:
    fields: dict[str, MergedField] = dc_field(default_factory=dict)

    def get_value(self, name: str):
        f = self.fields.get(name)
        return f.value if f else None


def merge_extraction(
    segment_text: str,
    segment_lines: list[str],
    llm_result: LLMExtractionResult | None,
    default_location: str,
) -> MergedProject:
    merged = MergedProject()

    # --- Deterministic pass ---
    labeled = deterministic.extract_labeled_fields(segment_lines)

    emails = deterministic.extract_emails(segment_text)
    if emails:
        merged.fields["email"] = MergedField(
            value=normalizer.normalize_email(emails[0]),
            source_text=emails[0],
            source_location=default_location,
            confidence=0.98,
            extraction_type="explicit",
        )

    if "telephone" in labeled:
        raw, source = labeled["telephone"]
        merged.fields["telephone"] = MergedField(
            value=normalizer.normalize_phone(raw),
            source_text=source,
            source_location=default_location,
            confidence=0.9,
            extraction_type="normalized",
        )

    currency_hits = deterministic.extract_currency_mentions(segment_text)
    if currency_hits:
        raw_number, unit, full_text = currency_hits[0]
        crore_value = normalizer.normalize_currency_to_crore(raw_number, unit)
        if crore_value is not None:
            merged.fields["contract_value_crore"] = MergedField(
                value=str(crore_value),
                source_text=full_text,
                source_location=default_location,
                confidence=0.9,
                extraction_type="normalized",
            )
            merged.fields["contract_value_original_text"] = MergedField(
                value=full_text, source_text=full_text, source_location=default_location,
                confidence=0.9, extraction_type="explicit",
            )

    if "start_date" in labeled:
        raw, source = labeled["start_date"]
        dates = deterministic.extract_dates(raw) or [raw]
        norm_value, precision = normalizer.normalize_date(dates[0])
        merged.fields["start_date"] = MergedField(
            value=norm_value, source_text=source, source_location=default_location,
            confidence=0.85 if precision != "unknown" else 0.5,
            extraction_type="normalized" if precision != "unknown" else "explicit",
        )

    if "completion_date" in labeled:
        raw, source = labeled["completion_date"]
        dates = deterministic.extract_dates(raw) or [raw]
        norm_value, precision = normalizer.normalize_date(dates[0])
        merged.fields["completion_date"] = MergedField(
            value=norm_value, source_text=source, source_location=default_location,
            confidence=0.85 if precision != "unknown" else 0.5,
            extraction_type="normalized" if precision != "unknown" else "explicit",
        )

    if "total_staff_months" in labeled:
        raw, source = labeled["total_staff_months"]
        merged.fields["total_staff_months"] = MergedField(
            value=raw, source_text=source, source_location=default_location,
            confidence=0.8, extraction_type="explicit",
        )

    if "client_address" in labeled:
        raw, source = labeled["client_address"]
        merged.fields["client_address"] = MergedField(
            value=raw, source_text=source, source_location=default_location,
            confidence=0.85, extraction_type="explicit",
        )

    if "contact_person" in labeled:
        raw, source = labeled["contact_person"]
        merged.fields["contact_person"] = MergedField(
            value=raw, source_text=source, source_location=default_location,
            confidence=0.8, extraction_type="explicit",
        )

    # Deterministic project_name/client_name (from labeled fields) as a
    # fallback if the LLM doesn't return one / LLM unavailable.
    for det_field, canonical in (("project_name", "project_name"), ("client_name", "client_name")):
        if det_field in labeled:
            raw, source = labeled[det_field]
            merged.fields.setdefault(
                canonical,
                MergedField(value=raw, source_text=source, source_location=default_location,
                            confidence=0.75, extraction_type="explicit"),
            )

    # --- LLM (semantic) pass - fills in / overrides remaining fields ---
    if llm_result is not None:
        semantic_fields = {
            "project_name": llm_result.project_name,
            "short_form": llm_result.short_form,
            "client_type": llm_result.client_type,
            "project_status": normalizer.normalize_project_status(llm_result.project_status),
            "client_name": llm_result.client_name,
            "project_description": llm_result.project_description,
            "actual_services": llm_result.actual_services,
            "associated_consultants": llm_result.associated_consultants,
            "senior_professional_staff": llm_result.senior_professional_staff,
            "country": llm_result.country,
            "state_ut": llm_result.state_ut,
        }
        for name, value in semantic_fields.items():
            if value is None:
                continue
            if name in ("project_name", "client_name") and name in merged.fields:
                continue  # deterministic explicit value already present, prefer it
            merged.fields[name] = MergedField(
                value=str(value),
                source_text=segment_text[:500],
                source_location=default_location,
                confidence=llm_result.confidence,
                extraction_type="explicit",
            )

    return merged
