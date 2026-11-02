"""
End-to-end test of the full pipeline: upload -> extract -> split -> AI
processing -> keywords -> search summary -> validation -> duplicate
detection -> review -> approve -> mock portal import -> verify DB -> verify
audit log. Uses FakeLLMProvider in place of real Ollama (not available in
CI/sandbox environments) and the real mock portal server (started in
conftest.py) so the production import path is exercised for real over HTTP.
"""
import io
import time

from docx import Document

from app.db.database import SessionLocal
from app.db.models.audit_log import AuditLog
from app.db.models.import_batch import ImportBatch
from app.db.models.project import ImportProject
from app.tests.fakes import FakeLLMProvider


def _build_sample_docx() -> bytes:
    doc = Document()
    doc.add_heading("AFC India - Company Experience Profile", level=1)

    # --- Newer-format project ---
    doc.add_paragraph("Assignment-1")
    doc.add_paragraph("Name of Applicant: AFC India Limited")
    doc.add_paragraph("Name of Project: National Level PACS Software Vendor")
    doc.add_paragraph(
        "Description of services Performed by the Applicant Firm: Design, development "
        "and rollout of an ERP platform for Primary Agricultural Credit Societies (PACS) "
        "including GIS-based branch mapping."
    )
    doc.add_paragraph("Name of client and Address: NABARD, Mumbai, Maharashtra")
    doc.add_paragraph("Name and telephone no. of client's representative: Mr. Sharma, 022-12345678")
    doc.add_paragraph("Estimated capital cost of the Project: Rs. 32.01 Crores")
    doc.add_paragraph("Start date: September 2021")
    doc.add_paragraph("Finish date: Ongoing")
    doc.add_paragraph(
        "Brief description of the Project: Nationwide ERP implementation for PACS "
        "digitization including GIS integration and data migration for NABARD."
    )

    # --- Older-format project ---
    doc.add_paragraph("Assignment-2")
    doc.add_paragraph("Assignment / Job name: Co-Working Spaces Portal Development")
    doc.add_paragraph("Firm's Name: AFC India Limited")
    doc.add_paragraph(
        "Description of Project: Development and maintenance of a portal for co-working "
        "spaces used by government agencies across India."
    )
    doc.add_paragraph("Approx. value of the Contract: Rs. 1.95 crore")
    doc.add_paragraph("Country & Location: India")
    doc.add_paragraph("Duration of Assignment / job: 24 months")
    doc.add_paragraph("Name of Employer: APCWS")
    doc.add_paragraph("Total No. of Staff months: 18")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _wait_for_batch_completion(client, headers, batch_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/imports/batches/{batch_id}", headers=headers)
        assert resp.status_code == 200
        if resp.json()["status"] in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
            return resp.json()
        time.sleep(0.5)
    raise TimeoutError("Batch did not complete in time")


def test_full_pipeline_upload_to_portal_import(client, contributor_headers, reviewer_headers, monkeypatch):
    # Use the fake local LLM provider so the test doesn't depend on a real
    # Ollama installation being present in this environment.
    import app.services.workflow.workflow_service as workflow_module

    monkeypatch.setattr(workflow_module, "OllamaProvider", lambda: FakeLLMProvider())

    docx_bytes = _build_sample_docx()
    resp = client.post(
        "/api/imports/batches",
        headers=contributor_headers,
        files={"files": ("company_experience.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 201, resp.text
    batch = resp.json()
    batch_id = batch["id"]

    final_batch = _wait_for_batch_completion(client, contributor_headers, batch_id)
    assert final_batch["projects_detected"] == 2

    projects_resp = client.get(f"/api/imports/batches/{batch_id}/projects", headers=contributor_headers)
    assert projects_resp.status_code == 200
    projects = projects_resp.json()
    assert len(projects) == 2

    pacs_project = next(p for p in projects if "PACS" in (p["project_name"] or "") or p["source_assignment_number"] == "Assignment-1")

    detail_resp = client.get(f"/api/projects/{pacs_project['id']}", headers=contributor_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    # --- Field extraction verification ---
    assert "NABARD" in (detail["client_name"] or "")
    assert detail["contract_value_crore"] == 32.01
    assert detail["start_date"] == "2021-09"
    assert detail["completion_date"] == "Ongoing"
    assert detail["project_status"] == "Ongoing"
    assert detail["source_assignment_number"] == "Assignment-1"

    # --- Keywords verification ---
    keyword_names = {k["keyword"] for k in detail["keywords"]}
    assert "GIS" in keyword_names or "ERP" in keyword_names

    # --- AI Search summary verification ---
    assert detail["ai_search_summary"]

    # --- Field provenance / source traceability ---
    assert detail["source_text"]
    assert any(f["field"] == "client_name" for f in detail["field_provenance"])

    # --- Approve + mock portal import ---
    assert detail["workflow_state"] in ("READY", "REVIEW_REQUIRED")
    approve_resp = client.post(
        f"/api/review/{pacs_project['id']}/approve", headers=reviewer_headers, json={"notes": "Looks good"}
    )
    assert approve_resp.status_code == 200
    approved = approve_resp.json()
    assert approved["workflow_state"] == "IMPORTED"

    db = SessionLocal()
    try:
        db_project = db.query(ImportProject).filter(ImportProject.id == pacs_project["id"]).first()
        assert db_project.portal_project_id is not None
        assert db_project.imported_at is not None

        audit_rows = db.query(AuditLog).filter(AuditLog.project_id == pacs_project["id"]).all()
        assert any(r.action == "APPROVE_PROJECT" for r in audit_rows)

        batch_row = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert batch_row.projects_detected == 2
    finally:
        db.close()


def test_idempotent_reimport_does_not_duplicate_on_portal(client, contributor_headers, reviewer_headers, monkeypatch):
    import app.services.workflow.workflow_service as workflow_module

    monkeypatch.setattr(workflow_module, "OllamaProvider", lambda: FakeLLMProvider())

    docx_bytes = _build_sample_docx()
    resp = client.post(
        "/api/imports/batches",
        headers=contributor_headers,
        files={"files": ("company_experience2.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    batch_id = resp.json()["id"]
    _wait_for_batch_completion(client, contributor_headers, batch_id)

    projects = client.get(f"/api/imports/batches/{batch_id}/projects", headers=contributor_headers).json()
    project_id = projects[0]["id"]

    first = client.post(f"/api/review/{project_id}/approve", headers=reviewer_headers, json={})
    assert first.status_code == 200
    portal_id_1 = first.json().get("portal_project_id")

    # Re-submitting the same already-imported project should be rejected by
    # the approve endpoint (already imported), proving no accidental re-post.
    second = client.post(f"/api/review/{project_id}/approve", headers=reviewer_headers, json={})
    assert second.status_code == 400
