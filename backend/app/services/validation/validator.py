from __future__ import annotations

from dataclasses import dataclass, field

CRITICAL_FIELDS = ["project_name", "client_name", "project_description"]


@dataclass
class ValidationResult:
    status: str  # PASSED | WARNING | FAILED
    warnings: list[str] = field(default_factory=list)
    missing_critical_fields: list[str] = field(default_factory=list)


def validate_project(project_data: dict) -> ValidationResult:
    warnings: list[str] = []
    missing = [f for f in CRITICAL_FIELDS if not project_data.get(f)]

    if missing:
        warnings.append(f"Missing critical fields: {', '.join(missing)}")

    if project_data.get("email") and "@" not in (project_data.get("email") or ""):
        warnings.append("Email format looks invalid.")

    if project_data.get("contract_value_crore") is not None and project_data["contract_value_crore"] < 0:
        warnings.append("Contract value is negative - flagged as ambiguous.")

    confidence = project_data.get("extraction_confidence")
    if confidence is not None and confidence < 0.5:
        warnings.append(f"Very low extraction confidence ({confidence:.0%}).")

    if not project_data.get("keywords"):
        warnings.append("No keywords were generated.")

    if missing:
        status = "FAILED" if len(missing) == len(CRITICAL_FIELDS) else "WARNING"
    elif warnings:
        status = "WARNING"
    else:
        status = "PASSED"

    return ValidationResult(status=status, warnings=warnings, missing_critical_fields=missing)
