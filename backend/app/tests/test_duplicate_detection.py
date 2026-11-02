import uuid

from app.db.database import SessionLocal
from app.db.models.import_batch import ImportBatch
from app.db.models.project import ImportProject
from app.db.models.source_document import SourceDocument
from app.db.models.user import User
from app.services.duplicate_detection.duplicate_service import find_duplicates


def _make_project(db, **overrides):
    defaults = dict(
        import_batch_id=overrides.pop("import_batch_id"),
        source_document_id=overrides.pop("source_document_id"),
        idempotency_key=str(uuid.uuid4()),
        workflow_state="IMPORTED",
        project_name="National Level PACS Software Vendor",
        client_name="NABARD",
        contract_value_crore=32.01,
        start_date="2021-09",
    )
    defaults.update(overrides)
    project = ImportProject(**defaults)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_find_duplicates_detects_likely_duplicate(db_session):
    user = db_session.query(User).first()
    batch = ImportBatch(created_by=user.id)
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    doc = SourceDocument(
        import_batch_id=batch.id, filename="x.docx", stored_path="/tmp/x.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=10, sha256="abc", uploaded_by=user.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    existing = _make_project(db_session, import_batch_id=batch.id, source_document_id=doc.id)

    candidate = _make_project(
        db_session, import_batch_id=batch.id, source_document_id=doc.id,
        project_name="National Level PACS Software Vendor", client_name="NABARD",
        contract_value_crore=32.01, start_date="2021-09", workflow_state="EXTRACTING",
    )

    finding = find_duplicates(db_session, candidate, "PACS ERP NABARD")
    assert finding.verdict in ("LIKELY_DUPLICATE", "POSSIBLE_DUPLICATE")
    assert finding.existing_project_id == existing.id


def test_find_duplicates_no_duplicate_for_unrelated_project(db_session):
    user = db_session.query(User).first()
    batch = ImportBatch(created_by=user.id)
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    doc = SourceDocument(
        import_batch_id=batch.id, filename="y.docx", stored_path="/tmp/y.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=10, sha256="def", uploaded_by=user.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    _make_project(db_session, import_batch_id=batch.id, source_document_id=doc.id)

    candidate = _make_project(
        db_session, import_batch_id=batch.id, source_document_id=doc.id,
        project_name="Highway Bridge Design Consultancy", client_name="NHAI",
        contract_value_crore=5.0, start_date="2015-01", workflow_state="EXTRACTING",
    )

    finding = find_duplicates(db_session, candidate, "highway bridge design")
    assert finding.verdict == "NO_DUPLICATE"
