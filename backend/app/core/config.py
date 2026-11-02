from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-me"
    app_database_url: str = "sqlite:///./storage/experience_intelligence.db"
    app_storage_dir: str = "./storage"
    app_max_upload_mb: int = 25
    app_cors_origins: str = "http://localhost:5173"

    access_token_expire_minutes: int = 480

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_timeout_seconds: int = 300

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_backend: str = "sentence-transformers"
    vector_store_dir: str = "./storage/chroma"

    auto_import_enabled: bool = False
    confidence_threshold: float = 0.85
    duplicate_likely_threshold: float = 0.90
    duplicate_possible_threshold: float = 0.75

    portal_import_url: str = "http://localhost:9000/api/internal/experience-import"
    portal_health_url: str = "http://localhost:9000/api/internal/health"
    portal_import_client_id: str = "experience-intelligence"
    portal_import_secret: str = "dev-shared-secret-change-me"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.app_storage_dir)
        p.mkdir(parents=True, exist_ok=True)
        (p / "uploads").mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.app_max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
