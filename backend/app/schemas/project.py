import datetime as dt

from pydantic import BaseModel

from app.schemas.extraction import FieldProvenance
from app.schemas.keyword import KeywordOut


class ProjectSummary(BaseModel):
    id: str
    project_name: str | None
    client_name: str | None
    project_status: str | None
    workflow_state: str
    extraction_confidence: float | None
    duplicate_status: str
    validation_status: str
    source_assignment_number: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class ProjectDetail(BaseModel):
    id: str
    import_batch_id: str
    source_document_id: str

    project_name: str | None = None
    short_form: str | None = None
    contract_value_crore: float | None = None
    contract_value_original_text: str | None = None
    country: str | None = None
    state_ut: str | None = None
    client_type: str | None = None
    project_status: str | None = None
    client_name: str | None = None
    client_address: str | None = None
    contact_person: str | None = None
    designation: str | None = None
    telephone: str | None = None
    email: str | None = None
    start_date: str | None = None
    completion_date: str | None = None
    duration_months: int | None = None
    total_staff_months: float | None = None
    professional_staff_months: float | None = None
    associated_consultants: str | None = None
    senior_professional_staff: str | None = None
    project_description: str | None = None
    actual_services: str | None = None

    ai_search_summary: str | None = None
    source_assignment_number: str | None = None
    source_filename: str | None = None
    source_page: str | None = None
    source_text: str | None = None
    source_location: str | None = None
    extraction_confidence: float | None = None
    extraction_type: str | None = None
    validation_status: str
    duplicate_status: str
    duplicate_of_project_id: str | None = None
    duplicate_similarity: float | None = None
    ai_model: str | None = None
    embedding_model: str | None = None

    workflow_state: str
    validation_warnings: list[str] = []
    failure_reason: str | None = None
    edited_by_human: bool = False

    portal_project_id: str | None = None
    imported_at: dt.datetime | None = None

    keywords: list[KeywordOut] = []
    field_provenance: list[FieldProvenance] = []

    created_at: dt.datetime
    updated_at: dt.datetime


class ProjectFieldEdit(BaseModel):
    field: str
    value: str | None


class ProjectUpdate(BaseModel):
    edits: list[ProjectFieldEdit]


class DuplicateCandidate(BaseModel):
    existing_project_id: str
    existing_project_name: str | None
    existing_client_name: str | None
    similarity: float
    matched_on: list[str]
