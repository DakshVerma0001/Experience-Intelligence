# Architecture

## System boundary

Experience Intelligence is a **standalone application**. It is not part of, and has no
direct dependency on, the production Knowledge Repository portal or its Supabase
database.

```
 Historical DOCX/PDF documents
            │
            ▼
 ┌─────────────────────────────┐
 │   Experience Intelligence    │   (this repository)
 │                              │
 │  React/TS frontend           │
 │  FastAPI backend             │
 │  SQLite (local app data)     │
 │  ChromaDB (local vectors)    │
 │  Ollama (local LLM)          │
 └──────────────┬───────────────┘
                │ HTTPS, service-to-service auth
                │ POST /api/internal/experience-import
                ▼
 ┌─────────────────────────────┐
 │  Existing Knowledge Repository│
 │  Portal (external system)     │
 │  "Experience Import Gateway"  │
 └──────────────┬───────────────┘
                ▼
            Supabase
```

Experience Intelligence never opens a connection to Supabase, never stores a
Supabase service-role key, and never stores a portal user's password. The
*only* integration point is the narrow, authenticated Experience Import
Gateway endpoint described in [portal-integration.md](portal-integration.md).

## Backend module layout

```
backend/app/
  api/routes/          FastAPI routers (one file per resource)
  core/                config, security (JWT/password hashing), logging
  db/                  SQLAlchemy models, repositories, Alembic migrations
  schemas/             Pydantic request/response and internal schemas
  services/
    document_parser/   DOCX (python-docx) and PDF (PyMuPDF + OCR fallback) parsing
    project_splitter/  Structural boundary detection ("Assignment-N", etc.)
    extraction/        Deterministic regex extraction + LLM extraction + normalization + merge
    enrichment/         Keyword generation, AI search summary generation
    embeddings/         Local embedding backend + local vector store (ChromaDB)
    duplicate_detection/ Name/client/date/value + keyword + semantic similarity comparison
    validation/         Field completeness / confidence validation
    import_gateway/     The ONLY code that talks to the production portal
    workflow/           Orchestrates the full pipeline end-to-end
    audit/              Writes audit log entries
  ai/                  LLM provider abstraction (Ollama implementation) + externalized prompts
```

## Processing pipeline

See [import-workflow.md](import-workflow.md) for the full state machine. In
short:

```
Upload → Parse → Split into project segments → Deterministic extraction
  → LLM (semantic) extraction → Merge + provenance → Keyword generation
  → AI search summary → Local embedding → Validation → Duplicate detection
  → Review / Auto-import decision → Portal import (if approved) → Audit log
```

Each project segment is processed **independently**, so a single project's
failure (e.g. malformed AI output, Ollama down) never aborts the rest of the
batch - it is marked `FAILED` with a reason and the batch continues.

## Why local AI

All LLM inference runs via [Ollama](https://ollama.com) on `localhost:11434`.
All embeddings run via a local `sentence-transformers` model. No document
content is ever sent to OpenAI, Anthropic, Google, or any other external AI
API. This is enforced structurally: the only network client that reaches
outside `localhost` in the processing pipeline is `portal_client.py`, and it
only sends the final *structured, reviewed* project data - never raw document
text - to the configured portal endpoint.

## Data storage

- **SQLite** (`backend/storage/experience_intelligence.db`) - all of
  Experience Intelligence's own application data: users, import batches,
  source documents, projects, extractions, keywords, review actions, audit
  logs, integration jobs, settings.
- **ChromaDB** (`backend/storage/chroma/`) - local vector store for semantic
  search, keyed by project ID.
- **Uploaded files** (`backend/storage/uploads/<batch_id>/`) - original
  DOCX/PDF documents, stored locally, never uploaded anywhere else.

None of this local storage is shared with, or derived from, the production
Supabase database.
