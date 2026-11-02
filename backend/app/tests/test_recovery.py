from app.db.models.import_batch import ImportBatch
from app.db.models.project import ImportProject
from app.db.models.source_document import SourceDocument
from app.db.models.user import User
from app.services.workflow.workflow_service import recover_interrupted_batches


def _make_batch_with_stuck_project(db, cancel_requested=False):
    user = db.query(User).first()
    batch = ImportBatch(created_by=user.id, status="PROCESSING", cancel_requested=cancel_requested)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    doc = SourceDocument(
        import_batch_id=batch.id, filename="orphan.docx", stored_path="/tmp/orphan.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=10, sha256=f"orphan-{batch.id}", uploaded_by=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    stuck = ImportProject(
        import_batch_id=batch.id, source_document_id=doc.id,
        idempotency_key=f"{batch.id}:stuck", workflow_state="EXTRACTING",
    )
    finished = ImportProject(
        import_batch_id=batch.id, source_document_id=doc.id,
        idempotency_key=f"{batch.id}:done", workflow_state="IMPORTED",
    )
    db.add_all([stuck, finished])
    db.commit()
    db.refresh(stuck)
    db.refresh(finished)
    return batch, stuck, finished


def test_recover_marks_stuck_projects_failed_and_batch_completed_with_errors(db_session):
    batch, stuck, finished = _make_batch_with_stuck_project(db_session, cancel_requested=False)

    recovered_count = recover_interrupted_batches(db_session)
    assert recovered_count >= 1

    db_session.refresh(batch)
    db_session.refresh(stuck)
    db_session.refresh(finished)

    assert stuck.workflow_state == "FAILED"
    assert "interrupted" in stuck.failure_reason.lower()
    assert finished.workflow_state == "IMPORTED"  # untouched - it already reached a terminal state
    assert batch.status == "COMPLETED_WITH_ERRORS"
    assert batch.projects_failed == 1


def test_recover_respects_prior_stop_request_as_cancelled(db_session):
    batch, stuck, finished = _make_batch_with_stuck_project(db_session, cancel_requested=True)

    recover_interrupted_batches(db_session)
    db_session.refresh(batch)

    assert batch.status == "CANCELLED"


def test_recover_is_a_noop_when_nothing_is_stuck(db_session):
    user = db_session.query(User).first()
    batch = ImportBatch(created_by=user.id, status="COMPLETED")
    db_session.add(batch)
    db_session.commit()

    # Should not touch already-terminal batches.
    recover_interrupted_batches(db_session)
    db_session.refresh(batch)
    assert batch.status == "COMPLETED"
