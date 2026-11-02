from pydantic import BaseModel


class ApproveRequest(BaseModel):
    notes: str | None = None


class RejectRequest(BaseModel):
    reason: str


class BulkApproveResult(BaseModel):
    approved_count: int
    imported_count: int
    skipped_review_required: int
    skipped_duplicate: int
    failed: list[str] = []


class DuplicateResolution(BaseModel):
    action: str  # "import_anyway" | "mark_duplicate" | "link_existing"
    existing_project_id: str | None = None
    notes: str | None = None
