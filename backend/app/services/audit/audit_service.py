from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    action: str,
    actor_user_id: str | None = None,
    actor_label: str | None = None,
    import_batch_id: str | None = None,
    project_id: str | None = None,
    source_document: str | None = None,
    ai_model: str | None = None,
    embedding_model: str | None = None,
    result: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Writes one audit record. Never include secrets/tokens/passwords or full
    client document contents in `details`."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        application="Experience Intelligence",
        action=action,
        import_batch_id=import_batch_id,
        project_id=project_id,
        source_document=source_document,
        ai_model=ai_model,
        embedding_model=embedding_model,
        result=result,
        details_json=json.dumps(details) if details else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
