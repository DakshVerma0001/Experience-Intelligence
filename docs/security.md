# Security Model

## Identity separation

Experience Intelligence has its **own** user accounts (`users` table, local
SQLite), completely separate from the production Knowledge Repository
portal's accounts. A user's Experience Intelligence password is never their
portal password, and is never transmitted to the portal.

If your organization later wants single sign-on between the two systems, the
integration point is `app/core/security.py` (`create_access_token`) and
`app/api/deps.py` (`get_current_user`) - replace local password verification
with validation of a token issued by your shared identity provider (e.g. the
portal's Supabase Auth via OIDC/JWT). Nothing else in the codebase needs to
change, because every route depends on the `get_current_user` /
`require_roles` dependencies rather than any specific auth mechanism.

## Roles

Three roles are enforced server-side via FastAPI dependencies
(`app/api/deps.py`):

| Role | Can |
|---|---|
| CONTRIBUTOR | Sign in, upload documents, create batches, view own batches, edit own extracted projects |
| REVIEWER | Everything CONTRIBUTOR can, plus: review queue, approve/reject, resolve duplicates, retry |
| ADMIN | Everything REVIEWER can, plus: manage users/roles, configure AI/import settings, view all batches, audit logs |

Role checks happen in the route layer (`require_roles(...)` dependencies),
never in the frontend alone - the React app hides UI a role can't use, but
the backend independently enforces it.

## No direct production access

Experience Intelligence's configuration (`backend/.env`) **must never
contain**:

- `SUPABASE_SERVICE_ROLE_KEY` or any Supabase key
- A production database connection string/password
- Production storage bucket credentials

These are structurally impossible to add accidentally because the app has no
Supabase client library, no database driver other than SQLite, and no code
path that constructs a Supabase URL.

## Service-to-service authentication to the portal

The only outbound integration is `app/services/import_gateway/portal_client.py`,
which:

1. Signs a short-lived (5 minute) JWT using `PORTAL_IMPORT_SECRET`
   (`app/core/security.py::create_service_token`).
2. Sends it as a `Bearer` token plus an `X-Client-Id` header.
3. Never sends a user's password, and never uses a browser/Selenium-style
   login.

The secret is read only from the environment, never logged, never returned
in any API response, and never sent to the frontend.

## Secret handling

- `backend/.env` is git-ignored (see `.gitignore`).
- `app/core/logging.py` installs a redacting log filter that replaces any
  `password=`, `secret=`, `token=`, `api_key=` value with `[REDACTED]` before
  it reaches stdout.
- JWTs are never logged; only high-level actions (`APPROVE_PROJECT`,
  `IMPORT_PROJECTS`, etc.) are written to the audit log, and audit records
  never contain full document text or credentials.

## Upload safety

- Only `.docx` and `.pdf` extensions and their expected MIME types are
  accepted (`app/api/routes/imports.py`).
- Filenames are sanitized (`_sanitize_filename`) before being used as a
  filesystem path component.
- File size is capped (`APP_MAX_UPLOAD_MB`, default 25MB).
- Uploaded files are stored on disk and parsed as *data* (python-docx /
  PyMuPDF) - they are never executed, evaluated, or passed to a shell.
- SHA-256 hashing detects when the exact same document is uploaded twice.

## Never fabricate

This is a security/data-integrity property as much as a data-quality one:
the LLM prompts (`app/ai/prompts/*.txt`) explicitly instruct the model to
return `null` for anything not explicitly present in the source text, and
the keyword generator (`app/services/enrichment/keyword_generator.py`)
programmatically drops any keyword that cannot be found in the source text -
this is enforced in code, not just prompted for.

## Two independent validation layers

Experience Intelligence validates extracted data before ever proposing an
import. The **production portal must independently re-validate** everything
it receives - see [portal-integration.md](portal-integration.md) and
[PORTAL_CHANGES_REQUIRED.md](PORTAL_CHANGES_REQUIRED.md). The AI application's
validation is never trusted as sufficient on the production side.
