from __future__ import annotations

import datetime as dt
import json
import uuid

from sqlalchemy.orm import Session

from app.ai.base import LLMUnavailableError
from app.ai.ollama import OllamaProvider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.import_batch import ImportBatch
from app.db.models.project import ImportProject, ProjectEmbedding, ProjectExtraction, ProjectKeyword
from app.db.models.source_document import SourceDocument
from app.services.audit import audit_service
from app.services.document_parser import get_parser_for
from app.services.document_parser.base import ParsedDocument
from app.services.duplicate_detection.duplicate_service import find_duplicates
from app.services.embeddings.embedding_service import build_embedding_input, get_embedding_backend, get_vector_store
from app.services.enrichment.keyword_generator import generate_keywords
from app.services.enrichment.search_summary import generate_search_summary
from app.services.extraction.field_merger import merge_extraction
from app.services.extraction.llm_extractor import ExtractionFailedError, extract_project_fields
from app.services.import_gateway.portal_client import get_portal_client
from app.services.project_splitter.splitter import ProjectSegment, split_into_projects
from app.schemas.integration import PortalImportPayload, PortalKeyword, PortalProjectPayload
from app.services.validation.validator import validate_project

logger = get_logger(__name__)

CRITICAL_FIELD_SET = {"project_name", "client_name", "project_description"}


def _parse_document(db: Session, doc: SourceDocument) -> ParsedDocument:
    parser = get_parser_for(doc.filename, doc.mime_type)
    if parser is None:
        doc.extraction_status = "FAILED"
        db.commit()
        raise ValueError(f"No parser available for {doc.filename}")

    parsed = parser.parse(doc.stored_path)
    doc.page_count = parsed.page_count
    doc.extraction_method = parsed.extraction_method
    doc.extraction_status = parsed.extraction_status
    db.commit()
    return parsed


def _process_segment(
    db: Session,
    batch: ImportBatch,
    doc: SourceDocument,
    segment: ProjectSegment,
    llm_provider: OllamaProvider,
) -> ImportProject:
    settings = get_settings()
    segment_lines = [b.text for b in segment.blocks]
    segment_text = segment.text
    default_location = segment.location_range

    idempotency_key = f"{batch.id}:{segment.source_assignment_number or uuid.uuid4().hex}"

    project = ImportProject(
        import_batch_id=batch.id,
        source_document_id=doc.id,
        source_assignment_number=segment.source_assignment_number,
        source_filename=doc.filename,
        source_page=str(segment.first_page) if segment.first_page else None,
        source_text=segment_text[:4000],
        source_location=default_location,
        workflow_state="EXTRACTING",
        idempotency_key=idempotency_key,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    try:
        return _run_segment_pipeline(db, batch, doc, segment, llm_provider, project, segment_lines, segment_text, default_location, settings)
    except Exception as exc:
        # Whatever stage this failed at (LLM timeout that somehow wasn't
        # wrapped, embedding backend error, DB hiccup, ...), never leave the
        # project stuck in an intermediate state like EXTRACTING/ENRICHING -
        # that reads as permanently "processing" in the UI with no way to
        # retry it. Always land on a terminal FAILED state instead.
        logger.exception("Unexpected error processing project %s", project.id)
        db.rollback()
        project = db.query(ImportProject).filter(ImportProject.id == project.id).first()
        project.workflow_state = "FAILED"
        project.failure_reason = f"Unexpected error during processing: {exc}"
        db.commit()
        return project


def _run_segment_pipeline(
    db: Session,
    batch: ImportBatch,
    doc: SourceDocument,
    segment: ProjectSegment,
    llm_provider: OllamaProvider,
    project: ImportProject,
    segment_lines: list[str],
    segment_text: str,
    default_location: str,
    settings,
) -> ImportProject:
    llm_result = None
    llm_error: str | None = None
    try:
        llm_result = extract_project_fields(llm_provider, segment_text)
    except LLMUnavailableError as exc:
        llm_error = str(exc)
        logger.warning("LLM unavailable for project %s: %s", project.id, exc)
    except ExtractionFailedError as exc:
        llm_error = str(exc)
        logger.warning("LLM extraction failed for project %s: %s", project.id, exc)

    merged = merge_extraction(segment_text, segment_lines, llm_result, default_location)

    for name in (
        "project_name", "short_form", "client_type", "project_status", "client_name",
        "client_address", "contact_person", "telephone", "email", "start_date", "completion_date",
        "total_staff_months", "project_description", "actual_services", "associated_consultants",
        "senior_professional_staff", "country", "state_ut", "contract_value_crore",
        "contract_value_original_text",
    ):
        mf = merged.fields.get(name)
        if mf is None:
            continue
        setattr(project, name, mf.value if name not in ("total_staff_months", "contract_value_crore") else _to_float(mf.value))
        db.add(
            ProjectExtraction(
                project_id=project.id,
                field_name=name,
                value=mf.value,
                source_text=mf.source_text,
                source_location=mf.source_location,
                confidence=mf.confidence,
                extraction_type=mf.extraction_type,
            )
        )

    confidences = [f.confidence for f in merged.fields.values() if f.confidence is not None]
    project.extraction_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    project.extraction_type = "explicit" if llm_result else "derived"
    project.ai_model = llm_provider.model if llm_result else None
    project.failure_reason = llm_error if not llm_result else None
    project.workflow_state = "ENRICHING"
    db.commit()

    # --- Enrichment: keywords + AI search summary (skipped gracefully if LLM down) ---
    keywords: list[dict] = []
    if llm_result is not None:
        try:
            keywords = generate_keywords(llm_provider, segment_text)
        except LLMUnavailableError:
            pass
        for kw in keywords:
            db.add(
                ProjectKeyword(
                    project_id=project.id,
                    keyword=kw["keyword"],
                    category=kw["category"],
                    description=kw["description"],
                    aliases=json.dumps(kw["aliases"]),
                    source_supported=kw["source_supported"],
                )
            )
        try:
            project.ai_search_summary = generate_search_summary(llm_provider, segment_text)
        except LLMUnavailableError:
            project.ai_search_summary = None
    db.commit()

    # --- Embeddings ---
    project.workflow_state = "EMBEDDING"
    db.commit()
    embed_input = build_embedding_input(
        {
            "project_name": project.project_name,
            "client_name": project.client_name,
            "project_description": project.project_description,
            "actual_services": project.actual_services,
            "keywords": [k["keyword"] for k in keywords],
            "keyword_descriptions": [k["description"] for k in keywords],
            "ai_search_summary": project.ai_search_summary,
            "country": project.country,
            "state_ut": project.state_ut,
        }
    )
    if embed_input.strip():
        backend = get_embedding_backend()
        vector = backend.embed(embed_input)
        get_vector_store().upsert(
            project.id,
            vector,
            metadata={"project_id": project.id, "batch_id": batch.id},
            document_text=embed_input,
        )
        db.add(
            ProjectEmbedding(
                project_id=project.id,
                embedding_model=backend.model_name,
                vector_store_collection="project_embeddings",
                dimensions=backend.dimensions,
                input_text_hash=str(hash(embed_input)),
            )
        )
        project.embedding_model = backend.model_name
        db.commit()

    # --- Validation ---
    project.workflow_state = "VALIDATING"
    validation_input = {
        "project_name": project.project_name,
        "client_name": project.client_name,
        "project_description": project.project_description,
        "email": project.email,
        "contract_value_crore": project.contract_value_crore,
        "extraction_confidence": project.extraction_confidence,
        "keywords": keywords,
    }
    validation = validate_project(validation_input)
    project.validation_status = validation.status
    project.validation_warnings = json.dumps(validation.warnings)
    db.commit()

    # --- Duplicate detection ---
    finding = find_duplicates(db, project, embed_input)
    project.duplicate_status = finding.verdict
    project.duplicate_of_project_id = finding.existing_project_id
    project.duplicate_similarity = finding.similarity
    db.commit()

    # --- Decide final pre-review state ---
    if not llm_result and llm_error:
        project.workflow_state = "FAILED"
        project.failure_reason = llm_error
    elif validation.status == "FAILED":
        project.workflow_state = "REVIEW_REQUIRED"
    elif finding.verdict in ("POSSIBLE_DUPLICATE", "LIKELY_DUPLICATE"):
        project.workflow_state = "DUPLICATE_REVIEW"
    elif validation.status == "WARNING":
        project.workflow_state = "REVIEW_REQUIRED"
    elif (project.extraction_confidence or 0) < settings.confidence_threshold:
        project.workflow_state = "REVIEW_REQUIRED"
    else:
        project.workflow_state = "READY"
    db.commit()
    return project


def _is_cancel_requested(db: Session, batch_id: str) -> bool:
    """Fresh, uncached read of just the cancel_requested flag - the ORM
    ImportBatch instance held for the duration of process_import_batch is
    loaded once and won't otherwise see a stop request set by a separate
    request/session while processing is in progress."""
    db.expire_all()
    value = db.query(ImportBatch.cancel_requested).filter(ImportBatch.id == batch_id).scalar()
    return bool(value)


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Non-terminal per-project states - i.e. states that only exist while
# process_import_batch's loop is actively working on that project.
_IN_PROGRESS_PROJECT_STATES = (
    "UPLOADED", "PARSING", "SPLITTING", "EXTRACTING", "ENRICHING", "VALIDATING", "EMBEDDING",
)


def recover_interrupted_batches(db: Session) -> int:
    """Runs once at application startup. Batch processing happens in a
    background task tied to the running process - if the process was
    killed or restarted while a batch was still PROCESSING, that task is
    gone for good and nothing will ever finish it or notice a stop request
    (this is exactly what "Stop Processing" doing nothing usually means).
    Rather than leave those batches/projects stuck forever, mark whatever
    was mid-flight as FAILED (individually retryable from the Review
    screen) and give the batch a terminal status."""
    stuck_batches = db.query(ImportBatch).filter(ImportBatch.status.in_(["UPLOADED", "PROCESSING"])).all()

    for batch in stuck_batches:
        stuck_projects = (
            db.query(ImportProject)
            .filter(
                ImportProject.import_batch_id == batch.id,
                ImportProject.workflow_state.in_(_IN_PROGRESS_PROJECT_STATES),
            )
            .all()
        )
        for project in stuck_projects:
            project.workflow_state = "FAILED"
            project.failure_reason = (
                "Processing was interrupted because the application restarted. "
                "Use Retry on this project to reprocess it."
            )

        all_projects = db.query(ImportProject).filter(ImportProject.import_batch_id == batch.id).all()
        batch.projects_detected = len(all_projects)
        batch.projects_failed = sum(1 for p in all_projects if p.workflow_state == "FAILED")
        batch.projects_review_required = sum(1 for p in all_projects if p.workflow_state == "REVIEW_REQUIRED")
        batch.projects_duplicate = sum(1 for p in all_projects if p.workflow_state == "DUPLICATE_REVIEW")
        batch.status = "CANCELLED" if batch.cancel_requested else "COMPLETED_WITH_ERRORS"
        db.commit()

        audit_service.record(
            db, action="BATCH_RECOVERED_AFTER_RESTART", import_batch_id=batch.id,
            result=batch.status, details={"stuck_projects_marked_failed": len(stuck_projects)},
        )
        logger.warning(
            "Recovered orphaned batch %s after restart: %s project(s) marked FAILED, batch -> %s",
            batch.id, len(stuck_projects), batch.status,
        )

    return len(stuck_batches)


def process_import_batch(db: Session, batch_id: str) -> ImportBatch:
    """Runs the full pipeline for every document in a batch: parse -> split ->
    extract -> enrich -> embed -> validate -> duplicate-check. One project
    failure never stops the rest of the batch."""
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise ValueError("Import batch not found")

    batch.status = "PROCESSING"
    db.commit()

    llm_provider = OllamaProvider()
    documents = db.query(SourceDocument).filter(SourceDocument.import_batch_id == batch_id).all()

    detected = auto_imported = review_required = duplicates = failed = 0
    cancelled = _is_cancel_requested(db, batch_id)

    for doc in documents:
        if _is_cancel_requested(db, batch_id):
            cancelled = True
            break

        try:
            parsed = _parse_document(db, doc)
        except Exception as exc:
            logger.exception("Failed to parse document %s", doc.filename)
            audit_service.record(
                db, action="DOCUMENT_PARSE_FAILED", import_batch_id=batch_id,
                source_document=doc.filename, result="FAILED", details={"error": str(exc)},
            )
            continue

        segments = split_into_projects(parsed)
        detected += len(segments)

        for segment in segments:
            if _is_cancel_requested(db, batch_id):
                cancelled = True
                break

            try:
                project = _process_segment(db, batch, doc, segment, llm_provider)
            except Exception as exc:
                logger.exception("Failed to process segment in %s", doc.filename)
                failed += 1
                audit_service.record(
                    db, action="PROJECT_PROCESSING_FAILED", import_batch_id=batch_id,
                    source_document=doc.filename, result="FAILED", details={"error": str(exc)},
                )
                continue

            if project.workflow_state == "FAILED":
                failed += 1
            elif project.workflow_state == "DUPLICATE_REVIEW":
                duplicates += 1
            elif project.workflow_state == "REVIEW_REQUIRED":
                review_required += 1
            elif project.workflow_state == "READY":
                if get_settings().auto_import_enabled:
                    auto_imported += 1  # actual portal submission happens in review routes/bulk-approve
                else:
                    review_required += 0  # stays READY, awaiting manual approve

        if cancelled:
            break

    batch.projects_detected = detected
    batch.projects_auto_imported = auto_imported
    batch.projects_review_required = review_required
    batch.projects_duplicate = duplicates
    batch.projects_failed = failed
    if cancelled:
        batch.status = "CANCELLED"
    else:
        batch.status = "COMPLETED_WITH_ERRORS" if failed else "COMPLETED"
    db.commit()

    audit_service.record(
        db, action="BATCH_CANCELLED" if cancelled else "BATCH_PROCESSED", import_batch_id=batch_id,
        ai_model=llm_provider.model, result=batch.status,
        details={"detected": detected, "failed": failed, "review_required": review_required},
    )

    settings = get_settings()
    if not cancelled and settings.auto_import_enabled:
        ready_ids = [
            p.id for p in db.query(ImportProject).filter(
                ImportProject.import_batch_id == batch_id, ImportProject.workflow_state == "READY"
            ).all()
        ]
        if ready_ids:
            import_projects_to_portal(db, ready_ids, initiated_by_label="AUTO_IMPORT_HIGH_CONFIDENCE")

    return batch


def _project_to_portal_payload(project: ImportProject, keywords: list[ProjectKeyword]) -> PortalProjectPayload:
    return PortalProjectPayload(
        idempotency_key=project.idempotency_key,
        project_name=project.project_name,
        short_form=project.short_form,
        contract_value_crore=project.contract_value_crore,
        country=project.country,
        state_ut=project.state_ut,
        client_type=project.client_type,
        project_status=project.project_status,
        client_name=project.client_name,
        client_address=project.client_address,
        contact_person=project.contact_person,
        designation=project.designation,
        telephone=project.telephone,
        email=project.email,
        start_date=project.start_date,
        completion_date=project.completion_date,
        duration_months=project.duration_months,
        total_staff_months=project.total_staff_months,
        professional_staff_months=project.professional_staff_months,
        associated_consultants=project.associated_consultants,
        senior_professional_staff=project.senior_professional_staff,
        project_description=project.project_description,
        actual_services=project.actual_services,
        ai_search_summary=project.ai_search_summary,
        keywords=[
            PortalKeyword(
                keyword=k.keyword,
                description=k.description,
                category=k.category,
                aliases=json.loads(k.aliases) if k.aliases else [],
            )
            for k in keywords
        ],
        source_assignment_number=project.source_assignment_number,
    )


def import_projects_to_portal(db: Session, project_ids: list[str], initiated_by_label: str) -> dict:
    """Submits READY/APPROVED projects to the production portal's Experience
    Import Gateway. Never talks to Supabase directly. Idempotent: each
    project's idempotency_key lets the portal safely dedupe retries."""
    from app.db.models.integration_job import IntegrationJob

    projects = db.query(ImportProject).filter(ImportProject.id.in_(project_ids)).all()
    if not projects:
        return {"submitted": 0, "succeeded": 0, "failed": 0}

    batch_id = projects[0].import_batch_id
    job = IntegrationJob(import_batch_id=batch_id, status="IN_PROGRESS", projects_submitted=len(projects))
    db.add(job)
    db.commit()
    db.refresh(job)

    payload_projects = []
    for project in projects:
        project.workflow_state = "IMPORTING"
        keywords = db.query(ProjectKeyword).filter(ProjectKeyword.project_id == project.id).all()
        payload_projects.append(_project_to_portal_payload(project, keywords))
    db.commit()

    payload = PortalImportPayload(batch_id=batch_id, initiated_by=initiated_by_label, projects=payload_projects)
    job.request_payload_json = payload.model_dump_json()
    job.attempt_count += 1
    db.commit()

    client = get_portal_client()
    succeeded = failed_count = 0
    try:
        response = client.submit_import(payload)
        job.response_payload_json = response.model_dump_json()
        by_key = {r.idempotency_key: r for r in response.results}
        for project in projects:
            result = by_key.get(project.idempotency_key)
            if result and result.status in ("created", "duplicate"):
                project.workflow_state = "IMPORTED"
                project.portal_project_id = result.portal_project_id
                project.imported_at = dt.datetime.now(dt.timezone.utc)
                succeeded += 1
            else:
                project.workflow_state = "FAILED"
                project.failure_reason = result.error if result else "No result returned by portal."
                failed_count += 1
            db.add(project)
        job.status = "SUCCESS" if failed_count == 0 else "FAILED"
    except Exception as exc:
        logger.exception("Portal import failed for batch %s", batch_id)
        job.status = "FAILED"
        job.error_message = str(exc)
        for project in projects:
            project.workflow_state = "FAILED"
            project.failure_reason = f"Portal import error: {exc}"
            failed_count += 1
        db.add_all(projects)

    job.projects_succeeded = succeeded
    job.projects_failed = failed_count
    job.completed_at = dt.datetime.now(dt.timezone.utc)
    db.commit()

    audit_service.record(
        db, action="IMPORT_PROJECTS", import_batch_id=batch_id,
        result=job.status, details={"submitted": len(projects), "succeeded": succeeded, "failed": failed_count},
    )
    return {"submitted": len(projects), "succeeded": succeeded, "failed": failed_count}
