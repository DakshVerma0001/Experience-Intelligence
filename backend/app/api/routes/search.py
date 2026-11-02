from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models.project import ImportProject, ProjectKeyword
from app.db.models.user import User
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.embeddings.embedding_service import get_embedding_backend, get_vector_store

router = APIRouter(prefix="/api/search", tags=["search"])

IMPORTED_STATES = ("IMPORTED", "READY", "APPROVED")


def _apply_filters(query, filters):
    if filters is None:
        return query
    if filters.country:
        query = query.filter(ImportProject.country == filters.country)
    if filters.state_ut:
        query = query.filter(ImportProject.state_ut == filters.state_ut)
    if filters.client_type:
        query = query.filter(ImportProject.client_type == filters.client_type)
    if filters.project_status:
        query = query.filter(ImportProject.project_status == filters.project_status)
    if filters.min_contract_value_crore is not None:
        query = query.filter(ImportProject.contract_value_crore >= filters.min_contract_value_crore)
    if filters.max_contract_value_crore is not None:
        query = query.filter(ImportProject.contract_value_crore <= filters.max_contract_value_crore)
    return query


def _keyword_search(db: Session, request: SearchRequest) -> list[tuple[ImportProject, float, list[str], list[str]]]:
    terms = [t.lower() for t in request.query.split() if len(t) > 1]
    query = db.query(ImportProject).filter(ImportProject.workflow_state.in_(IMPORTED_STATES))
    query = _apply_filters(query, request.filters)
    projects = query.all()

    results = []
    for project in projects:
        keywords = db.query(ProjectKeyword).filter(ProjectKeyword.project_id == project.id).all()
        keyword_texts = {k.keyword.lower() for k in keywords}
        matched = [k.keyword for k in keywords if k.keyword.lower() in terms or any(t in k.keyword.lower() for t in terms)]

        haystack = " ".join(
            filter(None, [project.project_name, project.project_description, project.actual_services, project.ai_search_summary])
        ).lower()
        text_hits = sum(1 for t in terms if t in haystack)
        keyword_hits = len(matched)

        score = (keyword_hits * 0.6 + text_hits * 0.4) / max(len(terms), 1)
        if score <= 0:
            continue
        reasons = matched[:8]
        results.append((project, min(score, 1.0), matched, reasons))
    return results


def _semantic_search(db: Session, request: SearchRequest) -> dict[str, float]:
    backend = get_embedding_backend()
    vector = backend.embed(request.query)
    hits = get_vector_store().query(vector, n_results=request.limit * 3)
    return dict(hits)


@router.post("", response_model=SearchResponse)
def search(request: SearchRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    keyword_hits = _keyword_search(db, request)
    keyword_scores = {p.id: (score, matched) for p, score, matched, _ in keyword_hits}
    projects_by_id = {p.id: p for p, *_ in keyword_hits}

    semantic_scores: dict[str, float] = {}
    if request.mode in ("semantic", "hybrid"):
        semantic_scores = _semantic_search(db, request)
        for pid, score in semantic_scores.items():
            if pid not in projects_by_id:
                project = db.query(ImportProject).filter(ImportProject.id == pid).first()
                if project and project.workflow_state in IMPORTED_STATES:
                    projects_by_id[pid] = project

    combined: list[SearchResultItem] = []
    for pid, project in projects_by_id.items():
        kw_score, matched = keyword_scores.get(pid, (0.0, []))
        sem_score = semantic_scores.get(pid, 0.0)

        if request.mode == "keyword" or request.mode == "fulltext":
            final_score = kw_score
        elif request.mode == "semantic":
            final_score = sem_score
        else:  # hybrid
            final_score = (kw_score * 0.5) + (sem_score * 0.5)

        if final_score <= 0:
            continue

        reasons = list(matched)
        if sem_score > 0.5 and request.mode in ("semantic", "hybrid"):
            reasons.append("Semantically similar project description")

        combined.append(
            SearchResultItem(
                project_id=project.id,
                project_name=project.project_name,
                client_name=project.client_name,
                country=project.country,
                state_ut=project.state_ut,
                ai_search_summary=project.ai_search_summary,
                score=round(final_score, 4),
                matched_keywords=matched,
                match_reasons=reasons,
            )
        )

    combined.sort(key=lambda r: r.score, reverse=True)
    return SearchResponse(query=request.query, mode=request.mode, results=combined[: request.limit])
