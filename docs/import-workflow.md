# Import Workflow

## End-to-end flow

```
USER LOGIN
  → UPLOAD DOCUMENT(S)               POST /api/imports/batches
  → CREATE IMPORT BATCH              (automatic)
  → EXTRACT TEXT                     document_parser/ (DOCX or PDF+OCR)
  → DETECT & SPLIT PROJECTS          project_splitter/
  → EXTRACT FIELDS                   extraction/deterministic.py + llm_extractor.py
  → GENERATE KEYWORDS                enrichment/keyword_generator.py
  → GENERATE KEYWORD DESCRIPTIONS    (part of the same step)
  → GENERATE AI SEARCH SUMMARY       enrichment/search_summary.py
  → GENERATE EMBEDDINGS              embeddings/embedding_service.py
  → VALIDATE                         validation/validator.py
  → DUPLICATE DETECTION              duplicate_detection/duplicate_service.py
  → CONFIDENCE ANALYSIS              (part of workflow_service.py)
  → REVIEW / AUTO-APPROVAL           review queue or AUTO_IMPORT_HIGH_CONFIDENCE
  → PRODUCTION IMPORT GATEWAY        import_gateway/portal_client.py
  → EXISTING PORTAL → SUPABASE       (external system)
  → AUDIT LOG                        audit/audit_service.py
```

All of the above (through duplicate detection) happens automatically and
synchronously in a background task per uploaded batch
(`app/services/workflow/workflow_service.py::process_import_batch`). The
frontend polls `GET /api/imports/batches/{id}/progress` every 2 seconds to
show live status.

## Stopping an in-progress batch

`POST /api/imports/batches/{id}/stop` (available from Import History and the
batch detail page while a batch is `UPLOADED` or `PROCESSING`) sets a
`cancel_requested` flag on the batch. The processing loop polls this flag
between documents and between individual project segments - it never
interrupts a project mid-extraction, but it stops starting any new
document/project as soon as it next checks. Projects already processed keep
whatever state they reached (`READY`, `REVIEW_REQUIRED`, etc.) and nothing is
rolled back; the batch itself ends in a `CANCELLED` status, and a
`BATCH_CANCELLED` audit record is written. A cancelled batch is not
auto-imported even if `AUTO_IMPORT_HIGH_CONFIDENCE` is enabled - any projects
that did reach `READY` before the stop still need manual approval.

## Per-project workflow states

```
UPLOADED → PARSING → SPLITTING → EXTRACTING → ENRICHING → VALIDATING
  → EMBEDDING → { REVIEW_REQUIRED | READY | DUPLICATE_REVIEW | FAILED }
  → APPROVED → IMPORTING → IMPORTED
  (or REJECTED at any review point)
```

A project lands in:

- **READY** - all critical fields present, confidence ≥ threshold, no
  duplicate, validation passed. Eligible for approval / auto-import.
- **REVIEW_REQUIRED** - missing critical fields, low confidence, or
  validation warnings.
- **DUPLICATE_REVIEW** - possible or likely duplicate of an already-imported
  project.
- **FAILED** - the LLM was unavailable or returned unusable output after
  retry, or an unexpected error occurred while processing this specific
  project. The rest of the batch is unaffected. Failed projects can be
  retried once the underlying issue (e.g. Ollama not running) is fixed, via
  `POST /api/review/{id}/retry`.

## Import policy

Configurable in Settings (Admin only) / `app/api/routes/settings.py`:

- `auto_import_enabled` (default **false** → `MANUAL_APPROVAL` mode)
- `confidence_threshold` (default 0.85)
- `duplicate_likely_threshold` / `duplicate_possible_threshold`

When `auto_import_enabled` is true (`AUTO_IMPORT_HIGH_CONFIDENCE` mode), any
project that reaches `READY` at the end of batch processing is automatically
submitted to the portal import gateway - see
`workflow_service.py::process_import_batch`.

## Review actions

- **Approve** (`POST /api/review/{id}/approve`) - moves the project to
  `APPROVED` then immediately submits it to the portal.
- **Reject** (`POST /api/review/{id}/reject`) - moves to `REJECTED` with a
  reason; never imported.
- **Resolve duplicate** (`POST /api/review/{id}/resolve-duplicate`) - either
  `import_anyway`, `mark_duplicate` (rejects), or `link_existing` (rejects
  and records the linked existing project ID). The existing project is never
  automatically modified or deleted.
- **Bulk approve** (`POST /api/review/batches/{batch_id}/approve-all-valid`) -
  approves and imports every `READY` project in the batch; projects still
  needing review or flagged as duplicates are left untouched.
- **Retry** (`POST /api/review/{id}/retry`) - re-runs extraction for a
  `FAILED` project against its original source segment.

## Idempotency

Every project gets an `idempotency_key` at creation time
(`{batch_id}:{assignment_number_or_random}`). This key is included in every
portal import payload. The mock portal (and the real portal, per the
contract in [portal-integration.md](portal-integration.md)) uses this key to
detect and safely handle retries/double-clicks without creating duplicate
production records.
