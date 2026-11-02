import datetime as dt

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    actor_label: str | None
    application: str
    action: str
    import_batch_id: str | None
    project_id: str | None
    source_document: str | None
    ai_model: str | None
    embedding_model: str | None
    result: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
