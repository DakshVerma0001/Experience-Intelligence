# Changes Required in the Production Portal

**Status: implemented.** See the "Status" section at the top of
[portal-integration.md](portal-integration.md) for what was actually built
(`D:\AFC-Automation\supabase\functions\experience-import`) and the deploy
commands to push it live. The checklist below is kept as the design record
of what each numbered requirement maps to.

Experience Intelligence is complete and independently runnable, but it can
only *propose* imports - it cannot write to Supabase. For approved projects
to actually appear in the production Knowledge Repository, the existing
portal codebase needs the following additions. This document is the
implementation checklist for the portal team; the exact request/response
contract they should implement is in
[portal-integration.md](portal-integration.md).

**The existing portal remains the sole authority for production data.**
Experience Intelligence does not, and should not, gain any other access.

## 1. Internal import endpoint ✅

`POST/GET supabase/functions/experience-import/index.ts`, matching the
schema in `docs/portal-integration.md`. (Edge Functions have one URL per
function; GET on that same URL serves as the health check instead of a
separate path - `/api/internal/import/{id}` was not needed since Experience
Intelligence tracks import results itself and doesn't currently poll the
portal for them.)

## 2. Service authentication ✅

`supabase/functions/_shared/serviceAuth.ts` verifies an HS256 JWT signed
with the `EXPERIENCE_IMPORT_SECRET` shared secret (`sub`, `aud`, `exp`
checked; not a Supabase user JWT, so the function is registered with
`verify_jwt = false` in `config.toml` and does its own verification). No
portal user session/cookie is accepted on this endpoint.

## 3. Request schema validation ✅

`validatePayload`/`validateProject` in `experience-import/index.ts` -
independent of whatever validation Experience Intelligence already did.
Invalid `schema_version` → `422`; invalid individual project → that
project's result is `"error"`, others in the batch are unaffected.

## 4. Project creation service ✅

Inserts into the same `projects`/`keywords`/`project_keyword_details` tables
`AddProjectPage.jsx` uses, via the Supabase admin (service-role) client -
not raw ad-hoc SQL, and respects the same `client_type`/`status` check
constraints (out-of-enum values are sanitized to `null` rather than erroring
the whole project).

## 5. Keyword creation ✅

Keywords are found-or-created by name and attached via
`project_keyword_details` with the AI-generated description.

## 6. Document attachment - not done (as scoped)

The current payload is metadata-only, as noted in the contract. Not
implemented; would need Experience Intelligence to expose signed document
URLs first.

## 7. Embedding/search metadata storage - partially done

Keywords + `ai_search_summary` are stored (the latter inside
`projects.summary.experienceIntelligence`, alongside batch/idempotency
traceability). The portal's own vector embedding
(`project_experience_embeddings`) is **not** computed by the edge function,
since that requires the in-browser `transformers.js` model. Run the portal's
existing "Rebuild Index" admin action after a bulk import to backfill it.

## 8. Duplicate/idempotency handling ✅

New table `experience_import_ledger` (migration
`20260927000000_experience_intelligence_import.sql`) maps
`idempotency_key → project_id`. A repeated key returns the original
`portal_project_id` instead of creating a second project.

## 9. Audit logging ✅

One `application_audit_log` row per imported project
(`action = 'experience_intelligence_import'`) plus one per-batch summary row
(`action = 'experience_intelligence_batch_import'`), both with
`action_by_role = 'experience-intelligence-service'` since there's no
`afc_users` row for the AI service.

## 10. RLS / security considerations

- The service account used by Experience Intelligence should have the
  **minimum** Supabase/RLS privileges needed to create projects, keywords,
  and audit records via the portal's own API layer - it should **not** be
  granted direct table access, and Experience Intelligence itself never
  receives Supabase credentials at all (it only calls this HTTP endpoint).
- Rate-limit and log all calls to this endpoint distinctly from normal user
  traffic. **Not yet implemented** - `_shared/publicAccess.ts`'s
  `checkRateLimit` helper (already used by other `verify_jwt = false`
  functions) would be a natural fit if this becomes a concern; skipped
  initially since the service token itself is the primary gate and only
  Experience Intelligence holds it.
- Consider IP allow-listing if Experience Intelligence runs on a known
  internal network. Not yet configured.
- Confirmed: the edge function uses the `service_role` key (full DB access,
  same as every other function in this project) rather than a scoped-down
  role - consistent with how `create-lead`, `create-staff-user`, etc.
  already operate here, but worth knowing this integration isn't more
  restricted than any other server-side function.

## Actual deploy steps

See the "Status" section at the top of
[portal-integration.md](portal-integration.md) for the real
`supabase secrets set` / `db push` / `functions deploy` commands, and its
"Reference implementation" test section for how it was verified (21 Deno
unit tests, `deno task test`, no live database touched).
