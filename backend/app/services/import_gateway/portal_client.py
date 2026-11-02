"""
The ONLY integration point with the production Knowledge Repository portal.
This client never touches Supabase directly, never stores a portal user
password, and never uses browser automation. It calls a narrowly-scoped
authenticated HTTP API (the "Experience Import Gateway") using a short-lived
signed service token - see docs/portal-integration.md.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import create_service_token
from app.schemas.integration import PortalImportPayload, PortalImportResponse

logger = get_logger(__name__)

MAX_RETRIES = 3


class PortalClient:
    def __init__(self):
        self.settings = get_settings()

    def _auth_headers(self) -> dict:
        token = create_service_token(
            self.settings.portal_import_client_id,
            self.settings.portal_import_secret,
            audience="experience-import-gateway",
        )
        return {
            "Authorization": f"Bearer {token}",
            "X-Client-Id": self.settings.portal_import_client_id,
            "Content-Type": "application/json",
        }

    def check_health(self) -> tuple[bool, str]:
        try:
            resp = httpx.get(self.settings.portal_health_url, timeout=5)
            resp.raise_for_status()
            return True, "Portal Import Gateway is reachable."
        except Exception as exc:
            return False, f"Portal Import Gateway unreachable: {exc}"

    def submit_import(self, payload: PortalImportPayload) -> PortalImportResponse:
        """POSTs the batch to the portal gateway. Retries transient failures.
        Idempotency is enforced via each project's idempotency_key - safe to
        retry the whole batch without creating duplicates on the portal side."""
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = httpx.post(
                    self.settings.portal_import_url,
                    headers=self._auth_headers(),
                    json=payload.model_dump(),
                    timeout=30,
                )
                if resp.status_code >= 500 and attempt < MAX_RETRIES:
                    logger.warning("Portal import attempt %s got %s, retrying...", attempt, resp.status_code)
                    continue
                resp.raise_for_status()
                return PortalImportResponse.model_validate(resp.json())
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code < 500:
                    raise  # 4xx = don't retry, it's a real validation/auth failure
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning("Portal import attempt %s network error: %s", attempt, exc)
        raise RuntimeError(f"Portal import failed after {MAX_RETRIES} attempts: {last_exc}")


def get_portal_client() -> PortalClient:
    return PortalClient()
