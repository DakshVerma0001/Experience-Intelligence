import time

from docx import Document
import io

from app.tests.fakes import FakeLLMProvider


def _build_multi_project_docx() -> bytes:
    doc = Document()
    for i in range(1, 4):
        doc.add_paragraph(f"Assignment-{i}")
        doc.add_paragraph(f"Name of Project: Test Project {i}")
        doc.add_paragraph(f"Name of Client: Client {i}")
        doc.add_paragraph("Description of Project: A test project description.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_stop_endpoint_rejects_non_stoppable_batch(client, contributor_headers, monkeypatch):
    import app.services.workflow.workflow_service as workflow_module

    monkeypatch.setattr(workflow_module, "OllamaProvider", lambda: FakeLLMProvider())

    docx_bytes = _build_multi_project_docx()
    resp = client.post(
        "/api/imports/batches",
        headers=contributor_headers,
        files={"files": ("stop_test.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    batch_id = resp.json()["id"]

    # By the time the (synchronous, in TestClient) background task finishes,
    # the batch is already COMPLETED - stop should now be rejected.
    for _ in range(30):
        status = client.get(f"/api/imports/batches/{batch_id}", headers=contributor_headers).json()["status"]
        if status not in ("UPLOADED", "PROCESSING"):
            break
        time.sleep(0.2)

    stop_resp = client.post(f"/api/imports/batches/{batch_id}/stop", headers=contributor_headers)
    assert stop_resp.status_code == 400


def test_stop_endpoint_requires_ownership_for_contributor(client, contributor_headers, reviewer_headers, monkeypatch):
    import app.services.workflow.workflow_service as workflow_module

    monkeypatch.setattr(workflow_module, "OllamaProvider", lambda: FakeLLMProvider())

    docx_bytes = _build_multi_project_docx()
    resp = client.post(
        "/api/imports/batches",
        headers=reviewer_headers,
        files={"files": ("stop_test2.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    batch_id = resp.json()["id"]

    # A different contributor (not the batch owner) cannot stop it.
    stop_resp = client.post(f"/api/imports/batches/{batch_id}/stop", headers=contributor_headers)
    assert stop_resp.status_code == 403


def test_cancel_requested_flag_is_respected_by_workflow(db_session):
    from app.db.models.import_batch import ImportBatch
    from app.db.models.source_document import SourceDocument
    from app.db.models.user import User
    from app.services.workflow.workflow_service import process_import_batch, _is_cancel_requested

    user = db_session.query(User).first()
    batch = ImportBatch(created_by=user.id, status="UPLOADED")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # No documents at all - process_import_batch should just complete
    # immediately either way; this test focuses on _is_cancel_requested
    # correctly reading a flag set via a separate flush.
    assert _is_cancel_requested(db_session, batch.id) is False

    batch.cancel_requested = True
    db_session.commit()

    assert _is_cancel_requested(db_session, batch.id) is True

    result = process_import_batch(db_session, batch.id)
    assert result.status == "CANCELLED"
