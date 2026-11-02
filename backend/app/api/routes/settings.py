from __future__ import annotations

from fastapi import APIRouter, Depends

from app.ai.ollama import OllamaProvider
from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models.system_settings import SystemSetting
from app.db.models.user import User
from app.schemas.settings import AISettings, ConnectionTestResult, ImportPolicySettings
from app.services.import_gateway.portal_client import get_portal_client
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_override(db: Session, key: str) -> str | None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else None


def _set_override(db: Session, key: str, value: str) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    db.commit()


@router.get("/import-policy", response_model=ImportPolicySettings)
def get_import_policy(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    settings = get_settings()
    auto_import = _get_override(db, "auto_import_enabled")
    threshold = _get_override(db, "confidence_threshold")
    return ImportPolicySettings(
        auto_import_enabled=(auto_import == "true") if auto_import is not None else settings.auto_import_enabled,
        confidence_threshold=float(threshold) if threshold is not None else settings.confidence_threshold,
        duplicate_likely_threshold=settings.duplicate_likely_threshold,
        duplicate_possible_threshold=settings.duplicate_possible_threshold,
    )


@router.put("/import-policy", response_model=ImportPolicySettings)
def update_import_policy(
    payload: ImportPolicySettings, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    _set_override(db, "auto_import_enabled", "true" if payload.auto_import_enabled else "false")
    _set_override(db, "confidence_threshold", str(payload.confidence_threshold))
    get_settings().auto_import_enabled = payload.auto_import_enabled  # in-process effective override
    get_settings().confidence_threshold = payload.confidence_threshold
    return payload


@router.get("/ai", response_model=AISettings)
def get_ai_settings(_admin: User = Depends(require_admin)):
    settings = get_settings()
    return AISettings(
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        embedding_model=settings.embedding_model,
        max_upload_mb=settings.app_max_upload_mb,
    )


@router.post("/test-ollama", response_model=ConnectionTestResult)
def test_ollama(_admin: User = Depends(require_admin)):
    ok, message = OllamaProvider().is_available()
    return ConnectionTestResult(ok=ok, message=message)


@router.post("/test-portal", response_model=ConnectionTestResult)
def test_portal(_admin: User = Depends(require_admin)):
    ok, message = get_portal_client().check_health()
    return ConnectionTestResult(ok=ok, message=message)
