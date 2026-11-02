from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.base import new_uuid, utcnow


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    import_batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batches.id"), index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    is_duplicate_upload: Mapped[bool] = mapped_column(default=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
