from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.database import get_db
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = Query(default=200, le=1000),
    import_batch_id: str | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = db.query(AuditLog)
    if import_batch_id:
        query = query.filter(AuditLog.import_batch_id == import_batch_id)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
