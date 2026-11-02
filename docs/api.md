# API Reference

Base URL: `http://localhost:8001` (see the port note in the README if you run
the backend on a different port). Interactive OpenAPI docs are always
available at `/docs` while the backend is running.

All endpoints except `/api/health` and `/api/auth/login` require
`Authorization: Bearer <token>`.

## Auth (`/api/auth`)

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/api/auth/login` | - | Email/password login, returns a JWT |
| GET | `/api/auth/me` | any | Current user |
| GET | `/api/auth/users` | ADMIN | List users |
| POST | `/api/auth/users` | ADMIN | Create a user |
| PATCH | `/api/auth/users/{id}/role` | ADMIN | Change a user's role |

## Imports (`/api/imports`)

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/api/imports/batches` | any | Upload 1+ DOCX/PDF files, creates a batch and starts processing |
| GET | `/api/imports/batches` | any (own for CONTRIBUTOR) | List batches |
| GET | `/api/imports/batches/{id}` | any | Batch detail |
| GET | `/api/imports/batches/{id}/progress` | any | Live processing progress (poll every ~2s) |
| POST | `/api/imports/batches/{id}/stop` | any (own for CONTRIBUTOR) | Requests processing stop; already-processed projects are kept, remaining ones are never started |
| GET | `/api/imports/batches/{id}/projects` | any | Projects detected in this batch |

## Review (`/api/review`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/api/review/queue` | REVIEWER/ADMIN | Projects needing review |
| POST | `/api/review/{id}/approve` | REVIEWER/ADMIN | Approve + submit to portal |
| POST | `/api/review/{id}/reject` | REVIEWER/ADMIN | Reject with reason |
| POST | `/api/review/{id}/resolve-duplicate` | REVIEWER/ADMIN | Resolve a duplicate flag |
| POST | `/api/review/{id}/retry` | REVIEWER/ADMIN | Retry a FAILED project |
| POST | `/api/review/batches/{batch_id}/approve-all-valid` | REVIEWER/ADMIN | Bulk-approve all READY projects |

## Projects (`/api/projects`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/api/projects/{id}` | any | Full project detail incl. keywords + field provenance |
| GET | `/api/projects/{id}/source` | any | Source document evidence |
| PATCH | `/api/projects/{id}` | any | Edit fields (preserves original AI value) |
| POST | `/api/projects/{id}/keywords` | any | Add a keyword |
| PATCH | `/api/projects/{id}/keywords/{kwId}` | any | Edit a keyword |
| DELETE | `/api/projects/{id}/keywords/{kwId}` | any | Delete a keyword |

## Search (`/api/search`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/search` | `{query, mode, filters, limit}` → ranked results with match reasons. `mode`: `keyword` \| `fulltext` \| `semantic` \| `hybrid` |

## Settings (`/api/settings`) - ADMIN

| Method | Path | Description |
|---|---|---|
| GET/PUT | `/api/settings/import-policy` | Auto-import + thresholds |
| GET | `/api/settings/ai` | Current Ollama/embedding config |
| POST | `/api/settings/test-ollama` | Live connectivity check |
| POST | `/api/settings/test-portal` | Live connectivity check |

## Audit (`/api/audit`) - ADMIN

| Method | Path | Description |
|---|---|---|
| GET | `/api/audit/logs?limit=&import_batch_id=&action=` | Filtered audit trail |

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | `{application, database, ollama, llm_model, embedding_model, portal}` |
