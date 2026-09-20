# Contract packet -- M04 attendance

Status: **APPROVED AND FROZEN** under revision `school-contracts-v5` on 2026-09-20
by Abhinav M. Artefacts live under `contracts/M04/`.

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** The module task must first
produce, for developer review:

1. the exact **OpenAPI** document for this module's REST API
2. the **JSON Schema** for every request, response and event payload
3. the **Protocol signatures** for every service port this module provides
4. the **error enums** -- which `code`/`message_key` pairs this module returns
5. **example fixtures** a consumer suite can assert against

Those are then **frozen in `contracts/manifest.json`** before implementation
starts. A later provider of the same contract must pass the same consumer
fixture suite. A mismatch needs a reviewed contract revision -- **not** an
invented per-module field and **not** a local adapter.

## What this module must declare

A `ModuleRegistration` in `backend/modules/attendance/registration.py`:

| field | meaning |
|---|---|
| `id` | `M04` |
| `slug` | `attendance` |
| `api_prefix` | `/api/attendance/` |
| `frontend_routes` | React routes, each with nav metadata and required permission |
| `permission_codes` | all namespaced `attendance.<verb>_<noun>` |
| `consumers` | service ports this module requires from others |
| `scheduled_jobs` | periodic work, cron interpreted in Asia/Kolkata |
| `migration_dependencies` | module ids whose migrations must apply first |
| `health_checks` | readiness probes contributed to `/readyz` |

## Inherited, non-negotiable constraints

These come from the foundation and are already enforced; a module does not
restate or relax them:

- UUID `id`, trusted `school_id`, integer `version` on mutable aggregates
- `expected_version` on every update; stale means **409**
- errors use the frozen envelope: 401 / 403 / 404 / 409 / 422
- **cross-school access is 404, never 403**
- collections return `items` + `next_cursor`; no offset pagination
- UTC instants, Asia/Kolkata civil dates, integer INR paise, decimal-string marks
- audit + outbox appended in the **same transaction** as the write
- Access checks apply to API, service, workers, exports and private files
- client role, school and relationship claims are never trusted
- `ResourceGrant` is server-internal and never accepted from a browser

## Standalone development

```bash
python scripts/dev.py up M04 --profile standalone
python scripts/dev.py migrate M04 --profile standalone
python scripts/dev.py seed M04 --scenario baseline
python scripts/dev.py check M04 --suite standalone
```

Dependency ports bind to deterministic fakes. Real authentication and 2FA
integration stay **explicitly pending** until M01 is integrated.

## B00 notes specific to this module

Attendance is required for EVERY period of the central timetable. This granularity is fixed by B00 and is not a per-deployment decision.

## Human gates before this module ships

- this packet reviewed and frozen in the manifest
- every equivalence/authorisation rule reviewed before being enabled
- the phase exit gate
- first customer-facing report for each design partner, where applicable
