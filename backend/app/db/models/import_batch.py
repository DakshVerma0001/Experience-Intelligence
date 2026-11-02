from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, event, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.base import new_uuid, utcnow

BATCH_STATUSES = (
    "UPLOADED",
    "PROCESSING",
    "COMPLETED",
    "COMPLETED_WITH_ERRORS",
    "CANCELLED",
    "FAILED",
)

# Statuses a "Stop" action is meaningful for - i.e. the batch is still doing
# (or about to do) work.
STOPPABLE_STATUSES = ("UPLOADED", "PROCESSING")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    batch_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    projects_detected: Mapped[int] = mapped_column(Integer, default=0)
    projects_auto_imported: Mapped[int] = mapped_column(Integer, default=0)
    projects_review_required: Mapped[int] = mapped_column(Integer, default=0)
    projects_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    projects_failed: Mapped[int] = mapped_column(Integer, default=0)
    # Set by POST /api/imports/batches/{id}/stop. The background processing
    # loop (workflow_service.process_import_batch) polls this between
    # documents/projects and stops starting new work once it sees it -
    # already-processed projects are left exactly as they are.
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


@event.listens_for(ImportBatch, "before_insert")
def _assign_batch_number(mapper, connection, target: ImportBatch) -> None:
    if target.batch_number is None:
        current_max = connection.execute(select(func.max(ImportBatch.batch_number))).scalar()
        target.batch_number = (current_max or 0) + 1
