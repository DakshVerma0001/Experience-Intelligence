from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.base import new_uuid, utcnow

# status: PENDING, IN_PROGRESS, SUCCESS, FAILED
class IntegrationJob(Base):
    __tablename__ = "integration_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    import_batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batches.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    projects_submitted: Mapped[int] = mapped_column(Integer, default=0)
    projects_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    projects_failed: Mapped[int] = mapped_column(Integer, default=0)
    request_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
