from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.base import new_uuid, utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    application: Mapped[str] = mapped_column(String(64), default="Experience Intelligence")
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    import_batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_document: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
