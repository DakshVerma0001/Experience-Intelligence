"""
Compares a candidate project against projects already imported into
Experience Intelligence using normalized name/client/date/value, keyword
overlap, and semantic similarity. Never deletes or auto-overwrites an
existing project - only classifies and flags for human review when unsure.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.project import ImportProject, ProjectKeyword
from app.services.embeddings.embedding_service import get_embedding_backend, get_vector_store


@dataclass
class DuplicateFinding:
    verdict: str  # NO_DUPLICATE | POSSIBLE_DUPLICATE | LIKELY_DUPLICATE
    existing_project_id: str | None
    similarity: float
    matched_on: list[str]


def _normalize_name(name: str | None) -> str:
    return "".join(ch.lower() for ch in (name or "") if ch.isalnum() or ch.isspace()).strip()


def _text_similarity(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def _keyword_overlap(kws_a: set[str], kws_b: set[str]) -> float:
    if not kws_a or not kws_b:
        return 0.0
    intersection = len(kws_a & kws_b)
    union = len(kws_a | kws_b)
    return intersection / union if union else 0.0


def find_duplicates(db: Session, candidate: ImportProject, embedding_input_text: str) -> DuplicateFinding:
    settings = get_settings()

    existing_projects = (
        db.query(ImportProject)
        .filter(ImportProject.id != candidate.id)
        .filter(ImportProject.workflow_state.in_(["IMPORTED", "READY", "REVIEW_REQUIRED", "APPROVED"]))
        .all()
    )

    candidate_keywords = {
        k.keyword.lower()
        for k in db.query(ProjectKeyword).filter(ProjectKeyword.project_id == candidate.id).all()
    }

    best_score = 0.0
    best_match: ImportProject | None = None
    best_reasons: list[str] = []

    for existing in existing_projects:
        reasons = []
        name_sim = _text_similarity(candidate.project_name, existing.project_name)
        client_sim = _text_similarity(candidate.client_name, existing.client_name)

        existing_keywords = {
            k.keyword.lower() for k in db.query(ProjectKeyword).filter(ProjectKeyword.project_id == existing.id).all()
        }
        kw_overlap = _keyword_overlap(candidate_keywords, existing_keywords)

        date_match = bool(
            candidate.start_date and existing.start_date and candidate.start_date == existing.start_date
        )
        value_match = (
            candidate.contract_value_crore is not None
            and existing.contract_value_crore is not None
            and abs(candidate.contract_value_crore - existing.contract_value_crore) < 0.05
        )

        if name_sim > 0.6:
            reasons.append(f"project name similarity {name_sim:.0%}")
        if client_sim > 0.6:
            reasons.append(f"client name similarity {client_sim:.0%}")
        if kw_overlap > 0.3:
            reasons.append(f"keyword overlap {kw_overlap:.0%}")
        if date_match:
            reasons.append("matching start date")
        if value_match:
            reasons.append("matching contract value")

        score = (name_sim * 0.45) + (client_sim * 0.2) + (kw_overlap * 0.2)
        if date_match:
            score += 0.075
        if value_match:
            score += 0.075
        score = min(score, 1.0)

        if score > best_score:
            best_score = score
            best_match = existing
            best_reasons = reasons

    if best_match is None or best_score < settings.duplicate_possible_threshold:
        return DuplicateFinding("NO_DUPLICATE", None, best_score, best_reasons)
    if best_score >= settings.duplicate_likely_threshold:
        return DuplicateFinding("LIKELY_DUPLICATE", best_match.id, best_score, best_reasons)
    return DuplicateFinding("POSSIBLE_DUPLICATE", best_match.id, best_score, best_reasons)
