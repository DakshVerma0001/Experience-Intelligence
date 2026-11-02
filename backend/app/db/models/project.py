from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.base import new_uuid, utcnow

# Workflow states
WORKFLOW_STATES = (
    "UPLOADED",
    "PARSING",
    "SPLITTING",
    "EXTRACTING",
    "ENRICHING",
    "VALIDATING",
    "EMBEDDING",
    "REVIEW_REQUIRED",
    "READY",
    "APPROVED",
    "IMPORTING",
    "IMPORTED",
    "REJECTED",
    "FAILED",
    "DUPLICATE_REVIEW",
)

DUPLICATE_STATES = ("NO_DUPLICATE", "POSSIBLE_DUPLICATE", "LIKELY_DUPLICATE")
VALIDATION_STATES = ("PENDING", "PASSED", "WARNING", "FAILED")


class ImportProject(Base):
    """Canonical internal schema mirroring the production Knowledge Repository,
    plus AI-specific provenance/metadata fields. This table is the AI app's own
    local copy — production data continues to live only in the portal's Supabase."""

    __tablename__ = "import_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    import_batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batches.id"), index=True)
    source_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("source_documents.id"), index=True)

    # --- Knowledge Repository schema fields ---
    project_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    short_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_value_crore: Mapped[float | None] = mapped_column(Float, nullable=True)
    contract_value_original_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state_ut: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # Ongoing/Completed/Cancelled/Unknown
    client_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)  # normalized YYYY-MM or YYYY-MM-DD or "Ongoing"
    completion_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_staff_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    professional_staff_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    associated_consultants: Mapped[str | None] = mapped_column(Text, nullable=True)
    senior_professional_staff: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_services: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- AI-specific metadata ---
    ai_search_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_assignment_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_page: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # explicit/derived/normalized
    validation_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    duplicate_status: Mapped[str] = mapped_column(String(32), default="NO_DUPLICATE")
    duplicate_of_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    duplicate_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # --- Workflow ---
    workflow_state: Mapped[str] = mapped_column(String(32), default="UPLOADED", index=True)
    validation_warnings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_by_human: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Production import tracking ---
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    portal_project_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    imported_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProjectExtraction(Base):
    """Field-level provenance: value, source_text, source_location, confidence,
    extraction_type. Preserves the original AI value even after human edits."""

    __tablename__ = "project_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_projects.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_original_ai_value: Mapped[bool] = mapped_column(Boolean, default=True)
    edited_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProjectKeyword(Base):
    __tablename__ = "project_keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_projects.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    source_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProjectEmbedding(Base):
    """Pointer/metadata record for the vector stored in the local vector store
    (ChromaDB). The vector itself lives in the vector store, not in SQLite."""

    __tablename__ = "project_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_projects.id"), unique=True, index=True)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_store_collection: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
