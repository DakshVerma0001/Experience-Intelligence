from pydantic import BaseModel


class ImportPolicySettings(BaseModel):
    auto_import_enabled: bool
    confidence_threshold: float
    duplicate_likely_threshold: float
    duplicate_possible_threshold: float
    require_review_for_every_project: bool = False
    require_review_for_missing_critical_fields: bool = True
    require_review_for_possible_duplicates: bool = True
    require_review_for_inferred_fields: bool = True


class AISettings(BaseModel):
    ollama_base_url: str
    ollama_model: str
    embedding_model: str
    max_upload_mb: int


class ConnectionTestResult(BaseModel):
    ok: bool
    message: str
    details: dict = {}
