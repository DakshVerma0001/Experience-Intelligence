# Experience Intelligence

An internal enterprise application that turns ~10 years of historical
DOCX/PDF project-experience documents into structured, searchable Knowledge
Repository records - automatically, using **local, private AI** (Ollama +
sentence-transformers), with a human review workflow and a safe, narrow
integration into the existing production Knowledge Repository portal.

## What it does

1. Accepts DOCX/PDF experience documents (drag-and-drop, multiple files).
2. Extracts text locally (python-docx / PyMuPDF, with OCR fallback for
   image-heavy PDF pages).
3. Detects and splits individual project/assignment records within a
   document, regardless of template/era.
4. Extracts fields using a **hybrid** approach: deterministic regex/rules for
   emails, phone numbers, currency, dates, assignment numbers; a local LLM
   (via Ollama) for semantic fields (project name, client, description,
   services, staff, etc.).
5. Normalizes values into the canonical Knowledge Repository schema, while
   always preserving the original source text.
6. Generates 5-15 source-supported search keywords per project, each with a
   description, category, and aliases.
7. Generates a 2-4 sentence AI Search Summary per project.
8. Generates local embeddings (sentence-transformers) and stores them in a
   local vector store (ChromaDB) for semantic search.
9. Flags missing/ambiguous fields and possible/likely duplicates for human
   review rather than guessing.
10. Provides a full review workflow: edit, approve, reject, resolve
    duplicates, bulk-approve, retry failures.
11. Automatically (or on manual approval) sends approved projects to the
    existing production Knowledge Repository via a narrow, authenticated
    HTTP API - **never** direct Supabase access, **never** browser
    automation, **never** the user's portal password.
12. Maintains a complete audit trail of every import, edit, approval,
    rejection, and production import result.

See [docs/architecture.md](docs/architecture.md) for the full system diagram
and [docs/security.md](docs/security.md) for the security model.

## Architecture at a glance

```
DOCX/PDF → Experience Intelligence (local AI, local DB) → Production Portal's
"Experience Import Gateway" (authenticated API) → Existing project-creation
logic → Supabase → Audit Log
```

Experience Intelligence is a **separate application**. It never connects
directly to production Supabase, never stores the Supabase service-role key,
and never stores production portal user passwords.

## Installation (Windows 10/11)

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/download) (for local AI; the app still runs
  without it, with reduced AI capability - see
  [docs/troubleshooting.md](docs/troubleshooting.md))

Check what you have:

```powershell
scripts\check-dependencies.ps1
```

### One-command setup

```powershell
scripts\setup-windows.ps1
```

This creates the backend virtual environment, installs Python dependencies,
copies `.env.example` → `.env`, and installs frontend npm dependencies.

### Pull the local LLM model

```powershell
scripts\setup-ollama.ps1
```

Pulls the model named in `backend/.env` (`OLLAMA_MODEL`, default
`llama3.1`). Change it to any model you have pulled (e.g. `mistral`,
`llama3.2`, `qwen2.5`).

## Running locally

You need **two** processes running (the production Knowledge Repository
portal at `D:\AFC-Automation` already implements the Experience Import
Gateway as a Supabase Edge Function - see
[docs/portal-integration.md](docs/portal-integration.md) - so a separate
mock portal process isn't needed unless you want to test offline).

**1. Backend** (port 8001):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

> Using port 8001 instead of the more common 8000 because Windows often
> reserves 8000 for Hyper-V/WSL dynamic port ranges, which causes
> `[WinError 10013] An attempt was made to access a socket in a way forbidden
> by its access permissions`. If 8001 is also blocked on your machine, see
> [docs/troubleshooting.md](docs/troubleshooting.md) for how to check
> Windows' excluded port ranges or just pick another free port (and update
> `frontend/vite.config.ts`'s proxy target to match).

On first start it prints a seeded default admin account - **change this
password immediately**:

```
admin@experience-intelligence.example / ChangeMe123!
```

**2. Frontend** (port 4521 - 5173 is already used by the Knowledge
Repository portal itself on this machine):

```powershell
cd frontend
npm run dev
```

Open http://localhost:4521.

### Pointing at the real portal vs. the mock portal

`backend/.env`'s `PORTAL_IMPORT_URL`/`PORTAL_HEALTH_URL` are set to the real
portal's deployed Edge Function, already live on the `afc-automation-dev`
Supabase project:

```
https://fmdhfbvjhhltcthziydl.supabase.co/functions/v1/experience-import
```

Verified end-to-end: an approved project really does land in that project's
`projects`/`keywords`/`application_audit_log` tables. Use
`Settings -> Test Portal Connection` in the app to re-check connectivity any
time, or fall back to the local mock portal for fully offline testing:

```powershell
python -m uvicorn mock_portal.main:app --port 9000
```

(and temporarily point `PORTAL_IMPORT_URL`/`PORTAL_HEALTH_URL` back at
`http://localhost:9000/...`).

## Environment variables

See `backend/.env.example` for the full list with defaults. Key ones:

| Variable | Purpose |
|---|---|
| `APP_DATABASE_URL` | Local SQLite database path |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Local LLM connection |
| `EMBEDDING_MODEL` | Local sentence-transformers model |
| `CONFIDENCE_THRESHOLD` / `AUTO_IMPORT_ENABLED` | Import policy defaults (also editable in Settings UI) |
| `PORTAL_IMPORT_URL` / `PORTAL_HEALTH_URL` | Production portal gateway endpoints |
| `PORTAL_IMPORT_CLIENT_ID` / `PORTAL_IMPORT_SECRET` | Service-to-service credentials (never a user password) |

`backend/.env` is git-ignored and must never be committed.

## Testing

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest app/tests -v
```

The test suite includes a full end-to-end test
(`app/tests/test_workflow_e2e.py`) that uploads a realistic multi-project
sample document, runs the entire pipeline (a fake local-LLM provider stands
in for Ollama so CI doesn't need a real model installed), approves a
project, and verifies it lands in a **real, running instance of the mock
portal** over HTTP - including idempotency.

Frontend type-checking / build:

```powershell
cd frontend
npm run typecheck
npm run build
```

## Sample data

`sample-data/company_experience_sample.docx` is a realistic sample document
with three differently-formatted assignments (newer template, older
template, and a completed project) - regenerate it any time with:

```powershell
cd scripts
python generate_sample_document.py
```

## Production deployment considerations

- Run the backend behind a real ASGI server (gunicorn+uvicorn workers or
  equivalent) and put it behind HTTPS.
- Move `AUTO_IMPORT_ENABLED`/thresholds to values your organization has
  validated - it defaults to conservative manual review.
- Point `PORTAL_IMPORT_URL`/`PORTAL_HEALTH_URL` at the real portal once it
  implements [docs/portal-integration.md](docs/portal-integration.md) (see
  [docs/PORTAL_CHANGES_REQUIRED.md](docs/PORTAL_CHANGES_REQUIRED.md) for what
  the portal team needs to build).
- Consider moving background processing off the request-handling process
  (e.g. a task queue) for very large documents/high concurrency - the
  current implementation uses FastAPI `BackgroundTasks`, which is sufficient
  for typical single-team internal usage.
- Back up `backend/storage/` (SQLite DB + ChromaDB + uploaded source
  documents) as part of your normal backup process.

## Documentation index

- [docs/architecture.md](docs/architecture.md)
- [docs/security.md](docs/security.md)
- [docs/import-workflow.md](docs/import-workflow.md)
- [docs/api.md](docs/api.md)
- [docs/portal-integration.md](docs/portal-integration.md)
- [docs/PORTAL_CHANGES_REQUIRED.md](docs/PORTAL_CHANGES_REQUIRED.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)

## Known limitations

- Live progress uses polling (every 2s), not Server-Sent Events.
- The offline export fallback (`experience-import-package.zip`) described in
  the product spec is not yet implemented as an API endpoint (the data it
  would contain - projects, keywords, validation report - is fully available
  via the API and could be assembled into a zip in a follow-up iteration).
- Contact-person extraction sometimes captures an adjoining phone number when
  a source document combines "name and telephone of representative" into a
  single label/value (visible in field provenance; safe to correct in the
  review UI).
- SSO with the production portal's identity provider is documented as an
  integration point (`docs/security.md`) but not implemented, since no
  existing IdP was available in this environment.
- OCR quality depends on the Tesseract binary being installed on the host
  machine; without it, OCR fallback is skipped gracefully and native PDF text
  extraction is used as-is.
