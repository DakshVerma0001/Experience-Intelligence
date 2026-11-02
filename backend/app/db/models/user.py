from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.base import new_uuid, utcnow

# Roles: CONTRIBUTOR, REVIEWER, ADMIN
ROLE_CONTRIBUTOR = "CONTRIBUTOR"
ROLE_REVIEWER = "REVIEWER"
ROLE_ADMIN = "ADMIN"
ALL_ROLES = (ROLE_CONTRIBUTOR, ROLE_REVIEWER, ROLE_ADMIN)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=ROLE_CONTRIBUTOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
