from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_reviewer
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models.project import ImportProject
from app.db.models.review_action import ReviewAction
from app.db.models.user import User
from app.schemas.project import ProjectSummary
from app.schemas.review import ApproveRequest, BulkApproveResult, DuplicateResolution, RejectRequest
from app.services.audit import audit_service
from app.services.workflow.workflow_service import import_projects_to_portal

router = APIRouter(prefix="/api/review", tags=["review"])

REVIEW_QUEUE_STATES = ["REVIEW_REQUIRED", "DUPLICATE_REVIEW", "FAILED"]


@router.get("/queue", response_model=list[ProjectSummary])
def get_review_queue(db: Session = Depends(get_db), _user: User = Depends(require_reviewer)):
    return (
        db.query(ImportProject)
        .filter(ImportProject.workflow_state.in_(REVIEW_QUEUE_STATES))
        .order_by(ImportProject.created_at.desc())
        .all()
    )


@router.post("/{project_id}/approve", response_model=ProjectSummary)
def approve_project(
    project_id: str, payload: ApproveRequest, db: Session = Depends(get_db), user: User = Depends(require_reviewer)
):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.workflow_state in ("IMPORTED", "IMPORTING"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Project already imported")

    project.workflow_state = "APPROVED"
    db.add(ReviewAction(project_id=project_id, user_id=user.id, action="APPROVE", notes=payload.notes))
    db.commit()

    result = import_projects_to_portal(db, [project_id], initiated_by_label=user.full_name)
    db.refresh(project)

    audit_service.record(
        db, action="APPROVE_PROJECT", actor_user_id=user.id, actor_label=user.full_name,
        project_id=project_id, import_batch_id=project.import_batch_id, result=project.workflow_state,
        details=result,
    )
    return project


@router.post("/{project_id}/reject", response_model=ProjectSummary)
def reject_project(
    project_id: str, payload: RejectRequest, db: Session = Depends(get_db), user: User = Depends(require_reviewer)
):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    project.workflow_state = "REJECTED"
    project.failure_reason = payload.reason
    db.add(ReviewAction(project_id=project_id, user_id=user.id, action="REJECT", notes=payload.reason))
    db.commit()
    db.refresh(project)

    audit_service.record(
        db, action="REJECT_PROJECT", actor_user_id=user.id, actor_label=user.full_name,
        project_id=project_id, import_batch_id=project.import_batch_id, result="REJECTED",
        details={"reason": payload.reason},
    )
    return project


@router.post("/{project_id}/resolve-duplicate", response_model=ProjectSummary)
def resolve_duplicate(
    project_id: str, payload: DuplicateResolution, db: Session = Depends(get_db), user: User = Depends(require_reviewer)
):
    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.workflow_state != "DUPLICATE_REVIEW":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Project is not pending duplicate review")

    db.add(
        ReviewAction(
            project_id=project_id, user_id=user.id, action="RESOLVE_DUPLICATE",
            notes=payload.notes, details_json=json.dumps(payload.model_dump()),
        )
    )

    if payload.action == "import_anyway":
        project.duplicate_status = "NO_DUPLICATE"
        project.workflow_state = "READY"
    elif payload.action == "mark_duplicate":
        project.workflow_state = "REJECTED"
        project.failure_reason = "Marked as duplicate during human review"
    elif payload.action == "link_existing":
        project.workflow_state = "REJECTED"
        project.duplicate_of_project_id = payload.existing_project_id
        project.failure_reason = "Linked to existing project; not imported"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid resolution action")

    db.commit()
    db.refresh(project)

    audit_service.record(
        db, action="RESOLVE_DUPLICATE", actor_user_id=user.id, actor_label=user.full_name,
        project_id=project_id, import_batch_id=project.import_batch_id, result=project.workflow_state,
    )
    return project


@router.post("/{project_id}/retry", response_model=ProjectSummary)
def retry_failed_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    from app.services.workflow.workflow_service import _process_segment  # noqa: local import to avoid cycle
    from app.db.models.import_batch import ImportBatch
    from app.db.models.source_document import SourceDocument
    from app.ai.ollama import OllamaProvider
    from app.services.document_parser import get_parser_for
    from app.services.project_splitter.splitter import split_into_projects

    project = db.query(ImportProject).filter(ImportProject.id == project_id).first()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.workflow_state != "FAILED":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only FAILED projects can be retried")

    doc = db.query(SourceDocument).filter(SourceDocument.id == project.source_document_id).first()
    batch = db.query(ImportBatch).filter(ImportBatch.id == project.import_batch_id).first()
    parser = get_parser_for(doc.filename, doc.mime_type)
    parsed = parser.parse(doc.stored_path)
    segments = split_into_projects(parsed)
    matching = next(
        (s for s in segments if s.source_assignment_number == project.source_assignment_number), None
    )
    if matching is None and segments:
        matching = segments[0]
    if matching is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not re-locate source segment for retry")

    db.delete(project)
    db.commit()

    new_project = _process_segment(db, batch, doc, matching, OllamaProvider())

    audit_service.record(
        db, action="RETRY_PROJECT", actor_user_id=user.id, actor_label=user.full_name,
        project_id=new_project.id, import_batch_id=batch.id, result=new_project.workflow_state,
    )
    return new_project


@router.post("/batches/{batch_id}/approve-all-valid", response_model=BulkApproveResult)
def approve_all_valid(batch_id: str, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    """Approves and imports every READY project in the batch. Projects still
    requiring review or flagged as duplicates are left untouched."""
    projects = db.query(ImportProject).filter(ImportProject.import_batch_id == batch_id).all()
    ready_ids = [p.id for p in projects if p.workflow_state == "READY"]
    review_required = sum(1 for p in projects if p.workflow_state == "REVIEW_REQUIRED")
    duplicates = sum(1 for p in projects if p.workflow_state == "DUPLICATE_REVIEW")

    for pid in ready_ids:
        p = db.query(ImportProject).filter(ImportProject.id == pid).first()
        p.workflow_state = "APPROVED"
        db.add(ReviewAction(project_id=pid, user_id=user.id, action="APPROVE", notes="Bulk approve"))
    db.commit()

    result = import_projects_to_portal(db, ready_ids, initiated_by_label=user.full_name) if ready_ids else {
        "submitted": 0, "succeeded": 0, "failed": 0
    }

    audit_service.record(
        db, action="BULK_APPROVE", actor_user_id=user.id, actor_label=user.full_name,
        import_batch_id=batch_id, result="SUCCESS", details=result,
    )

    return BulkApproveResult(
        approved_count=len(ready_ids),
        imported_count=result["succeeded"],
        skipped_review_required=review_required,
        skipped_duplicate=duplicates,
        failed=[],
    )
