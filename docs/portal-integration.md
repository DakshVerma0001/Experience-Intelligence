# Portal Integration Contract

This document defines the contract between Experience Intelligence and the
existing production Knowledge Repository portal's **Experience Import
Gateway**. It is the single source of truth both sides must implement
against. A reference implementation (`mock_portal/main.py`) exists so
Experience Intelligence can be fully developed and tested without touching
the real portal.

## Status: implemented in the real portal

The portal (`D:\AFC-Automation`, a Vite/React app backed by Supabase, with
server-side logic living in Supabase Edge Functions - there is no separate
Node/Express backend) now implements this contract as a Supabase Edge
Function:

```
D:\AFC-Automation\supabase\functions\experience-import\index.ts
D:\AFC-Automation\supabase\functions\_shared\serviceAuth.ts   (HS256 service-token verification)
D:\AFC-Automation\supabase\migrations\20260927000000_experience_intelligence_import.sql  (idempotency ledger)
```

It reuses the exact same tables `AddProjectPage.jsx` writes to
(`projects`, `keywords`, `project_keyword_details`) via the Supabase
admin/service-role client, so AI-imported and manually-added projects are
indistinguishable to the rest of the portal. Deployed URL:

```
POST/GET https://fmdhfbvjhhltcthziydl.supabase.co/functions/v1/experience-import
```

(GET = health check, unauthenticated; POST = import, requires the signed
service token described below.)

**To deploy/update it** (run from `D:\AFC-Automation`, not automated by
Experience Intelligence's own setup since it touches a live Supabase
project):

```powershell
supabase secrets set EXPERIENCE_IMPORT_SECRET=<the value in Experience Intelligence's backend/.env PORTAL_IMPORT_SECRET>
supabase secrets set EXPERIENCE_IMPORT_CLIENT_ID=experience-intelligence
supabase db push
supabase functions deploy experience-import
```

**Known gap:** the function does not compute the portal's own semantic-
search embedding (`project_experience_embeddings` - that requires the
in-browser `transformers.js` model, see `src/lib/embeddingModel.js`). After
a bulk import, run the portal's existing admin **"Rebuild Index"** action
(`RebuildIndexPanel.jsx`) once to backfill search for the newly imported
projects. Document attachment is also not implemented (the payload is
metadata-only today).

The rest of this document is the stable contract - useful whether you're
looking at the real implementation above or testing against
`mock_portal/main.py`.

## Endpoint

```
POST {PORTAL_IMPORT_URL}   e.g. https://portal.example.com/api/internal/experience-import
GET  {PORTAL_HEALTH_URL}   e.g. https://portal.example.com/api/internal/health
```

## Authentication

Service-to-service only - **never** a user's password.

- Experience Intelligence signs a short-lived (5 minute) JWT with a shared
  secret (`PORTAL_IMPORT_SECRET`), `aud=experience-import-gateway`,
  `sub=PORTAL_IMPORT_CLIENT_ID`.
- Sent as `Authorization: Bearer <jwt>` plus `X-Client-Id: <client id>`.
- The portal verifies the signature, audience, expiry, and that the client ID
  is a known/allowed integration.

## Request schema (`schema_version: "1.0"`)

```json
{
  "schema_version": "1.0",
  "batch_id": "uuid",
  "initiated_by": "string (display name or AUTO_IMPORT_HIGH_CONFIDENCE)",
  "projects": [
    {
      "idempotency_key": "string - stable per project, safe to retry on",
      "project_name": "string | null",
      "short_form": "string | null",
      "contract_value_crore": "number | null",
      "country": "string | null",
      "state_ut": "string | null",
      "client_type": "string | null",
      "project_status": "Ongoing | Completed | Cancelled | Unknown | null",
      "client_name": "string | null",
      "client_address": "string | null",
      "contact_person": "string | null",
      "designation": "string | null",
      "telephone": "string | null",
      "email": "string | null",
      "start_date": "string | null",
      "completion_date": "string | null",
      "duration_months": "integer | null",
      "total_staff_months": "number | null",
      "professional_staff_months": "number | null",
      "associated_consultants": "string | null",
      "senior_professional_staff": "string | null",
      "project_description": "string | null",
      "actual_services": "string | null",
      "ai_search_summary": "string | null",
      "keywords": [
        { "keyword": "string", "description": "string | null", "category": "string | null", "aliases": ["string"] }
      ],
      "source_assignment_number": "string | null"
    }
  ]
}
```

Full Pydantic definition: `backend/app/schemas/integration.py`.

## Response schema

```json
{
  "batch_id": "uuid",
  "results": [
    { "idempotency_key": "string", "status": "created | duplicate | error", "portal_project_id": "string | null", "error": "string | null" }
  ]
}
```

## Errors

| HTTP status | Meaning | Experience Intelligence behavior |
|---|---|---|
| 401 | Auth failed | No retry; surfaced to admin via Settings → Test Portal Connection |
| 403 | Unknown/disallowed client | No retry |
| 422 / per-project `status: "error"` | Schema/business validation failed | That project is marked FAILED with the error message; others in the batch are unaffected |
| 5xx | Transient portal error | Retried up to 3 times with backoff (`portal_client.py`) |

## Idempotency

Every project carries a stable `idempotency_key`
(`{import_batch_id}:{source_assignment_number_or_generated_id}`). If the
portal receives a request with a key it has already processed successfully,
it **must** return the original result (`status: "created"` with the same
`portal_project_id`) rather than creating a second record. This makes it safe
for Experience Intelligence to retry an entire batch submission after a
timeout, or for a user to click "Approve" twice.

## Duplicate handling

`status: "duplicate"` is treated by Experience Intelligence the same as
`"created"` (the project is marked `IMPORTED`) - the portal is expected to
have its own duplicate policy and Experience Intelligence defers to it for
anything that reaches the gateway. Experience Intelligence's own duplicate
detection (against projects it has already imported) happens *before* this
call, in the review workflow.

## Transactionality

On the portal side, a single project's import (project row + keywords +
document attachment + embedding/search metadata + audit record) **must** be
written in one database transaction. If any part fails, the whole write
rolls back and that project's result is `"error"` - never a partially
created record.

## Audit requirements

The portal should record, per import: which service account performed the
write (`experience-intelligence`), the batch ID, the idempotency key, and the
resulting `portal_project_id`. Experience Intelligence separately records its
own audit trail (`GET /api/audit/logs`) including who approved the project
and when.

## Reference implementation

`mock_portal/main.py` is a complete, runnable implementation of this
contract for local development/testing:

```
python -m uvicorn mock_portal.main:app --port 9000
```

It supports simulating failure modes for testing:

```
POST http://localhost:9000/api/internal/test-mode?mode=validation_error
# modes: success | validation_error | duplicate | auth_failure | server_error
```
