import datetime as dt

from pydantic import BaseModel


class ImportBatchOut(BaseModel):
    id: str
    batch_number: int
    status: str
    created_by: str
    projects_detected: int
    projects_auto_imported: int
    projects_review_required: int
    projects_duplicate: int
    projects_failed: int
    cancel_requested: bool
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class ProcessingProgress(BaseModel):
    batch_id: str
    status: str
    documents_uploaded: int
    documents_processed: int
    projects_detected: int
    projects_processed: int
    current_step: str | None
    warnings: list[str] = []
    failures: list[str] = []
