"""Regression test for a real bug: if _run_segment_pipeline raises partway
through (e.g. an LLM call that times out without being wrapped as
LLMUnavailableError), the project must never be left stuck in an
intermediate state like EXTRACTING - it must land on FAILED with a reason,
so it shows up as retryable instead of "processing" forever."""
from app.ai.base import LLMProvider, LLMResponse
from app.db.database import SessionLocal
from app.db.models.import_batch import ImportBatch
from app.db.models.project import ImportProject
from app.db.models.source_document import SourceDocument
from app.db.models.user import User
from app.services.document_parser.base import ExtractedBlock
from app.services.project_splitter.splitter import ProjectSegment
from app.services.workflow.workflow_service import _process_segment


class ExplodingLLMProvider(LLMProvider):
    model = "exploding-model"

    def is_available(self):
        return True, "ok"

    def generate(self, prompt: str, *, temperature: float = 0.1) -> LLMResponse:
        raise RuntimeError("simulated unwrapped failure (e.g. a raw timeout)")


def test_unexpected_exception_never_orphans_the_project(db_session):
    user = db_session.query(User).first()
    batch = ImportBatch(created_by=user.id, status="PROCESSING")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    doc = SourceDocument(
        import_batch_id=batch.id, filename="explode.docx", stored_path="/tmp/explode.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=10, sha256="explode-hash", uploaded_by=user.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    segment = ProjectSegment(
        source_assignment_number="Assignment-1",
        blocks=[ExtractedBlock(text="Name of Project: X", block_type="paragraph", location="paragraph 1")],
    )

    project = _process_segment(db_session, batch, doc, segment, ExplodingLLMProvider())

    assert project.workflow_state == "FAILED"
    assert "unexpected error" in project.failure_reason.lower()

    # Confirm it's really persisted, not just the in-memory object.
    fresh_db = SessionLocal()
    try:
        reloaded = fresh_db.query(ImportProject).filter(ImportProject.id == project.id).first()
        assert reloaded.workflow_state == "FAILED"
    finally:
        fresh_db.close()
