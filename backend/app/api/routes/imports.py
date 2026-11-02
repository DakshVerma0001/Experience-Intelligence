from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models.import_batch import STOPPABLE_STATUSES, ImportBatch
from app.db.models.project import ImportProject
from app.db.models.source_document import SourceDocument
from app.db.models.user import User
from app.schemas.import_batch import ImportBatchOut, ProcessingProgress
from app.schemas.project import ProjectSummary
from app.services.audit import audit_service
from app.services.workflow.workflow_service import process_import_batch

router = APIRouter(prefix="/api/imports", tags=["imports"])

ALLOWED_EXTENSIONS = {".docx", ".pdf"}
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf",
}
_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    return _UNSAFE_CHARS_RE.sub("_", base) or "upload"


@router.post("/batches", response_model=ImportBatchOut, status_code=status.HTTP_201_CREATED)
async def create_import_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "At least one file is required")

    settings = get_settings()
    batch = ImportBatch(created_by=user.id, status="UPLOADED")
    db.add(batch)
    db.commit()
    db.refresh(batch)

    batch_dir = settings.storage_path / "uploads" / batch.id
    batch_dir.mkdir(parents=True, exist_ok=True)

    for upload in files:
        filename = _sanitize_filename(upload.filename or "upload")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {filename}")

        content = await upload.read()
        if len(content) == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Empty file: {filename}")
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File too large: {filename}")

        mime_type = upload.content_type or ""
        if mime_type and mime_type not in ALLOWED_MIME_TYPES and ext == ".docx":
            mime_type = list(ALLOWED_MIME_TYPES)[0]
        elif ext == ".pdf":
            mime_type = "application/pdf"

        sha256 = hashlib.sha256(content).hexdigest()
        is_duplicate = db.query(SourceDocument).filter(SourceDocument.sha256 == sha256).first() is not None

        stored_path = batch_dir / filename
        stored_path.write_bytes(content)

        doc = SourceDocument(
            import_batch_id=batch.id,
            filename=filename,
            stored_path=str(stored_path),
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=sha256,
            is_duplicate_upload=is_duplicate,
            uploaded_by=user.id,
        )
        db.add(doc)

    db.commit()

    audit_service.record(
        db, action="BATCH_UPLOADED", actor_user_id=user.id, actor_label=user.full_name,
        import_batch_id=batch.id, result="SUCCESS", details={"file_count": len(files)},
    )

    background_tasks.add_task(_run_processing, batch.id)
    return batch


def _run_processing(batch_id: str) -> None:
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        process_import_batch(db, batch_id)
    finally:
        db.close()


@router.get("/batches", response_model=list[ImportBatchOut])
def list_batches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(ImportBatch)
    if user.role == "CONTRIBUTOR":
        query = query.filter(ImportBatch.created_by == user.id)
    return query.order_by(ImportBatch.created_at.desc()).all()


@router.get("/batches/{batch_id}", response_model=ImportBatchOut)
def get_batch(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import batch not found")
    if user.role == "CONTRIBUTOR" and batch.created_by != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your import batch")
    return batch


@router.post("/batches/{batch_id}/stop", response_model=ImportBatchOut)
def stop_batch(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Requests that in-progress processing stop. The background pipeline
    (workflow_service.process_import_batch) polls this flag between
    documents/projects and stops starting new work once it sees it -
    projects already processed are left exactly as they are; nothing is
    rolled back."""
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import batch not found")
    if user.role == "CONTRIBUTOR" and batch.created_by != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your import batch")
    if batch.status not in STOPPABLE_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Batch is already {batch.status}; nothing to stop.")

    batch.cancel_requested = True
    db.commit()
    db.refresh(batch)

    audit_service.record(
        db, action="BATCH_STOP_REQUESTED", actor_user_id=user.id, actor_label=user.full_name,
        import_batch_id=batch_id, result="REQUESTED",
    )
    return batch


@router.get("/batches/{batch_id}/progress", response_model=ProcessingProgress)
def get_batch_progress(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import batch not found")

    docs = db.query(SourceDocument).filter(SourceDocument.import_batch_id == batch_id).all()
    projects = db.query(ImportProject).filter(ImportProject.import_batch_id == batch_id).all()

    docs_processed = sum(1 for d in docs if d.extraction_status in ("SUCCESS", "PARTIAL", "FAILED"))
    processed_states = {"READY", "REVIEW_REQUIRED", "DUPLICATE_REVIEW", "IMPORTED", "FAILED", "APPROVED"}
    projects_processed = sum(1 for p in projects if p.workflow_state in processed_states)

    warnings = []
    failures = []
    for p in projects:
        if p.workflow_state == "FAILED":
            failures.append(f"{p.source_assignment_number or p.id}: {p.failure_reason or 'Unknown error'}")
        if p.validation_warnings:
            import json

            warnings.extend(json.loads(p.validation_warnings))

    current_step = None
    in_progress = [p for p in projects if p.workflow_state not in processed_states]
    if in_progress:
        current_step = f"{in_progress[0].workflow_state.title()} {in_progress[0].source_assignment_number or ''}".strip()
    elif batch.status == "PROCESSING":
        current_step = "Parsing documents"

    return ProcessingProgress(
        batch_id=batch_id,
        status=batch.status,
        documents_uploaded=len(docs),
        documents_processed=docs_processed,
        projects_detected=len(projects),
        projects_processed=projects_processed,
        current_step=current_step,
        warnings=warnings[:50],
        failures=failures[:50],
    )


@router.get("/batches/{batch_id}/projects", response_model=list[ProjectSummary])
def list_batch_projects(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ImportProject).filter(ImportProject.import_batch_id == batch_id).order_by(
        ImportProject.created_at
    ).all()
