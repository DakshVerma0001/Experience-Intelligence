# Troubleshooting

## `GET /api/health` shows `"ollama": false`

Ollama is not running or not installed. Extraction still runs (deterministic
fields like name, dates, currency, email, phone, assignment number are
unaffected), but semantic fields, keywords, and AI search summaries will not
be generated, and projects will be marked `FAILED` with reason "Ollama is not
running." Install Ollama (https://ollama.com/download), then:

```powershell
scripts\setup-ollama.ps1
```

and confirm `ollama list` shows the model named in `backend/.env`
(`OLLAMA_MODEL`).

## `"llm_model": false` but Ollama is running

The configured `OLLAMA_MODEL` isn't pulled yet. Run:

```powershell
ollama pull <model-name>
```

## `"embedding_model"` shows an error

`sentence-transformers` failed to load the configured model (first run needs
internet access to download it once; afterwards it's cached locally under
`~/.cache/huggingface`). If it's still unavailable, Experience Intelligence
falls back to a deterministic local hashing embedding
(`embedding_service.py::HashingFallbackBackend`) so search keeps working,
just with lower semantic quality - check backend logs for the fallback
warning.

## `"portal": false`

The mock portal (or your real portal) isn't reachable at `PORTAL_HEALTH_URL`.
For local development, start it:

```powershell
python -m uvicorn mock_portal.main:app --port 9000
```

## Upload fails with 400 "Unsupported file type"

Only `.docx` and `.pdf` are accepted. Convert `.doc`/`.rtf` files to `.docx`
first.

## A batch stays stuck on "PROCESSING"

Processing runs in a FastAPI background task in the same process as the
backend. If the backend process crashed mid-batch, restart it; already-
completed projects are preserved, and you can retry `FAILED` ones
individually from the Review screen.

## Projects come back with very low confidence / many REVIEW_REQUIRED

This is expected for older/unusual document formats the deterministic
extractor doesn't recognize a label for, and is *by design* - Experience
Intelligence flags for review rather than guessing. Check "View Source" on
the project to see exactly what text it had, and edit the field manually if
needed.

## `pip install` fails on `chromadb` / `sentence-transformers`

These packages need a working C/Rust toolchain on some platforms. If your
Python version is very new and prebuilt wheels aren't published yet, either
use a slightly older, more widely-supported Python (3.11-3.12) or wait for
upstream wheels. Search still functions without them via the local hashing
fallback (see above), but with reduced result quality.

## Frontend shows CORS or "Failed to fetch" errors

Ensure the backend is running at `http://localhost:8001` (or whichever port
you chose) and that `frontend/vite.config.ts`'s proxy `target` matches it.
Also confirm `APP_CORS_ORIGINS` in `backend/.env` includes
`http://localhost:5173`. If you're running the frontend dev server on a
different port, add it to the same setting.

## `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`

This is Windows refusing the bind - it is **not** the usual "port already in
use" error (that's `WinError 10048`). Common causes:

1. **The port falls in a Windows-reserved dynamic range**, most often
   because Hyper-V or WSL2 has reserved it. Check with:
   ```powershell
   netsh interface ipv4 show excludedportrange protocol=tcp
   ```
   If your port is inside a listed range, pick a port outside all of them
   (the app defaults to 8001 for the backend for this reason - see the
   README's port note).
2. **A firewall or antivirus product is blocking the bind.** Temporarily
   disable it to confirm, then add an allow rule for `python.exe`/`uvicorn`
   if that's the cause.
3. **The port requires elevated privileges.** Ports below 1024 need an
   Administrator shell; anything 1024+ (like 8001) normally doesn't, but some
   security tools restrict specific ports regardless.

To use a different port for the backend, update:
- The `uvicorn app.main:app --reload --port <port>` command
- `frontend/vite.config.ts`'s `server.proxy["/api"].target`

## "Session expired" immediately after logging in

Check that `backend/.env`'s `APP_SECRET_KEY` hasn't changed between when the
token was issued and now (changing it invalidates all existing tokens - this
is expected after a fresh `.env` setup).
