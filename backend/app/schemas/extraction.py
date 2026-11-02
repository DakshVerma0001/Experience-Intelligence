from pydantic import BaseModel


class FieldProvenance(BaseModel):
    field: str
    value: str | None = None
    source_text: str | None = None
    source_location: str | None = None
    confidence: float | None = None
    extraction_type: str | None = None  # explicit | derived | normalized
    edited_by_human: bool = False

    model_config = {"from_attributes": True}


class LLMExtractionResult(BaseModel):
    """Strict schema the LLM must return (validated before use anywhere)."""

    project_name: str | None = None
    short_form: str | None = None
    client_type: str | None = None
    project_status: str | None = None
    client_name: str | None = None
    project_description: str | None = None
    actual_services: str | None = None
    associated_consultants: str | None = None
    senior_professional_staff: str | None = None
    country: str | None = None
    state_ut: str | None = None
    confidence: float = 0.0
