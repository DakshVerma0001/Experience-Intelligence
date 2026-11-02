"""
Mock production Knowledge Repository "Experience Import Gateway".

This is a LOCAL STAND-IN for the real portal endpoint described in
docs/portal-integration.md, used for development and end-to-end testing
without touching the real production portal/Supabase. It implements the
same request/response contract Experience Intelligence's portal_client.py
expects, including auth, schema validation, idempotency, and simulated
failure modes.

Run: uvicorn mock_portal.main:app --port 9000
"""
from __future__ import annotations

import uuid

import jwt
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Mock Knowledge Repository Portal")

SHARED_SECRET = "dev-shared-secret-change-me"  # must match PORTAL_IMPORT_SECRET
EXPECTED_CLIENT_ID = "experience-intelligence"

# In-memory "production" project store + idempotency ledger, for local testing only.
_PROJECTS: dict[str, dict] = {}
_IDEMPOTENCY_LEDGER: dict[str, str] = {}  # idempotency_key -> portal_project_id

# Toggle to simulate specific failure modes during testing/demo.
SIMULATE_MODE = {"mode": "success"}  # success | validation_error | duplicate | auth_failure | server_error


class PortalKeyword(BaseModel):
    keyword: str
    description: str | None = None
    category: str | None = None
    aliases: list[str] = Field(default_factory=list)


class PortalProjectPayload(BaseModel):
    idempotency_key: str
    project_name: str | None
    short_form: str | None = None
    contract_value_crore: float | None = None
    country: str | None = None
    state_ut: str | None = None
    client_type: str | None = None
    project_status: str | None = None
    client_name: str | None = None
    client_address: str | None = None
    contact_person: str | None = None
    designation: str | None = None
    telephone: str | None = None
    email: str | None = None
    start_date: str | None = None
    completion_date: str | None = None
    duration_months: int | None = None
    total_staff_months: float | None = None
    professional_staff_months: float | None = None
    associated_consultants: str | None = None
    senior_professional_staff: str | None = None
    project_description: str | None = None
    actual_services: str | None = None
    ai_search_summary: str | None = None
    keywords: list[PortalKeyword] = Field(default_factory=list)
    source_assignment_number: str | None = None


class PortalImportPayload(BaseModel):
    schema_version: str
    batch_id: str
    initiated_by: str
    projects: list[PortalProjectPayload]


class PortalProjectResult(BaseModel):
    idempotency_key: str
    status: str
    portal_project_id: str | None = None
    error: str | None = None


class PortalImportResponse(BaseModel):
    batch_id: str
    results: list[PortalProjectResult]


def _authenticate(authorization: str | None, x_client_id: str | None) -> None:
    if SIMULATE_MODE["mode"] == "auth_failure":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Simulated authentication failure")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        jwt.decode(token, SHARED_SECRET, algorithms=["HS256"], audience="experience-import-gateway")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid service token: {exc}")
    if x_client_id != EXPECTED_CLIENT_ID:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown client id")


def _validate_project(project: PortalProjectPayload) -> str | None:
    """Portal-side validation - never trusts the AI application's own
    validation. Returns an error string if invalid, else None."""
    if not project.project_name or not project.project_name.strip():
        return "project_name is required"
    if not project.client_name or not project.client_name.strip():
        return "client_name is required"
    if project.contract_value_crore is not None and project.contract_value_crore < 0:
        return "contract_value_crore cannot be negative"
    if project.email and "@" not in project.email:
        return "email format is invalid"
    return None


@app.get("/api/internal/health")
def health():
    return {"portal": True, "mode": SIMULATE_MODE["mode"]}


@app.post("/api/internal/test-mode")
def set_simulation_mode(mode: str):
    valid = {"success", "validation_error", "duplicate", "auth_failure", "server_error"}
    if mode not in valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"mode must be one of {valid}")
    SIMULATE_MODE["mode"] = mode
    return {"mode": mode}


@app.post("/api/internal/experience-import", response_model=PortalImportResponse)
def experience_import(
    payload: PortalImportPayload,
    authorization: str | None = Header(default=None),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
):
    _authenticate(authorization, x_client_id)

    if SIMULATE_MODE["mode"] == "server_error":
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Simulated server error")

    results: list[PortalProjectResult] = []

    for project in payload.projects:
        # --- Idempotency: same key returns the same prior result, never a new record. ---
        if project.idempotency_key in _IDEMPOTENCY_LEDGER:
            results.append(
                PortalProjectResult(
                    idempotency_key=project.idempotency_key,
                    status="created",
                    portal_project_id=_IDEMPOTENCY_LEDGER[project.idempotency_key],
                )
            )
            continue

        if SIMULATE_MODE["mode"] == "validation_error":
            results.append(
                PortalProjectResult(idempotency_key=project.idempotency_key, status="error", error="Simulated validation error")
            )
            continue

        error = _validate_project(project)
        if error:
            results.append(PortalProjectResult(idempotency_key=project.idempotency_key, status="error", error=error))
            continue

        if SIMULATE_MODE["mode"] == "duplicate":
            results.append(
                PortalProjectResult(idempotency_key=project.idempotency_key, status="duplicate", error="Simulated duplicate in production")
            )
            continue

        # --- Transactional "write": project + keywords + audit record together. ---
        portal_project_id = f"KR-{uuid.uuid4().hex[:10]}"
        _PROJECTS[portal_project_id] = {
            **project.model_dump(),
            "portal_project_id": portal_project_id,
            "imported_batch_id": payload.batch_id,
            "initiated_by": payload.initiated_by,
        }
        _IDEMPOTENCY_LEDGER[project.idempotency_key] = portal_project_id

        results.append(
            PortalProjectResult(idempotency_key=project.idempotency_key, status="created", portal_project_id=portal_project_id)
        )

    return PortalImportResponse(batch_id=payload.batch_id, results=results)


@app.get("/api/internal/import/{portal_project_id}")
def get_imported_project(portal_project_id: str):
    project = _PROJECTS.get(portal_project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return project


@app.get("/api/internal/_debug/projects")
def debug_list_projects():
    """Test-only introspection endpoint - not part of the real portal contract."""
    return {"count": len(_PROJECTS), "projects": list(_PROJECTS.values())}
