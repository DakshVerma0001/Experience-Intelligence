from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class PortalKeyword(BaseModel):
    keyword: str
    description: str | None = None
    category: str | None = None
    aliases: list[str] = Field(default_factory=list)


class PortalProjectPayload(BaseModel):
    idempotency_key: str
    project_name: str | None
    short_form: str | None = None
    contract_value_crore: float | None = None
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
    keywords: list[PortalKeyword] = Field(default_factory=list)
    source_assignment_number: str | None = None


class PortalImportPayload(BaseModel):
    schema_version: str = SCHEMA_VERSION
    batch_id: str
    initiated_by: str
    projects: list[PortalProjectPayload]


class PortalProjectResult(BaseModel):
    idempotency_key: str
    status: str  # created | duplicate | error
    portal_project_id: str | None = None
    error: str | None = None


class PortalImportResponse(BaseModel):
    batch_id: str
    results: list[PortalProjectResult]
