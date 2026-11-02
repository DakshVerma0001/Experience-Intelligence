from fastapi import APIRouter
from sqlalchemy import text

from app.ai.ollama import OllamaProvider
from app.core.config import get_settings
from app.db.database import SessionLocal
from app.services.embeddings.embedding_service import get_embedding_backend
from app.services.import_gateway.portal_client import get_portal_client

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check():
    settings = get_settings()

    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False

    ollama_ok, ollama_message = OllamaProvider().is_available()

    embedding_ok = True
    embedding_message = "OK"
    try:
        backend = get_embedding_backend()
        embedding_message = f"Using {backend.model_name}"
    except Exception as exc:
        embedding_ok = False
        embedding_message = str(exc)

    portal_ok, portal_message = get_portal_client().check_health()

    return {
        "application": True,
        "database": db_ok,
        "ollama": ollama_ok,
        "ollama_message": ollama_message,
        "llm_model": ollama_ok,
        "embedding_model": embedding_ok,
        "embedding_message": embedding_message,
        "portal": portal_ok,
        "portal_message": portal_message,
        "environment": settings.app_env,
    }
