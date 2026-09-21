# Contract packet -- M14 platform

Status: **PROPOSED — awaiting human freeze**. Artefacts exist; `contracts/manifest.json`
lists them with `frozen: false`. Do **not** implement until a named reviewer
approves `review-decisions.md` and freezes under `school-contracts-v15`.

Manifest revision this packet targets: `school-contracts-v14` (current) →
proposed freeze revision `school-contracts-v15`.

Branched from `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`).

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** Artefacts below are proposed
for review:

### Checklist — proposed artefacts

| # | Artefact | Path | Status |
|---|---|---|---|
| 1 | OpenAPI 3.1.0 | `openapi.json` | proposed |
| 2 | Request/response DTOs | `schemas/dtos.schema.json` | proposed |
| 3 | Event payloads | `schemas/events.schema.json` | proposed |
| 4 | Error rows | `error-codes.json` | proposed |
| 5 | Service ports | `ports.md` | proposed |
| 6 | Review decisions | `review-decisions.md` | proposed |
| 7 | Seed scenario | `fixtures/scenario.json` | proposed |
| 8 | Example responses | `fixtures/responses.json` | proposed |
| 9 | Acceptance assertions | `fixtures/expected-results.json` | proposed |

## Module registration

| field | value |
|---|---|
| id | `M14` |
| slug | `platform` |
| api_prefix | `/api/v1/` |
| api_path_roots | `health/`, `jobs/`, `audit/`, `operations/` |
| permission_codes | `platform.read_health`, `jobs.read`, `jobs.retry`, `audit.read`, `backups.manage` |
| permission_prefixes | `platform.`, `jobs.`, `audit.`, `backups.` |
| consumers | access, clock (+ local object store for backup versions) |
| public_paths | `health/live` |
| scheduled_jobs | outbox dispatcher; backup age monitor (Asia/Kolkata cron) |

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
python scripts/dev.py up M14 --profile standalone
python scripts/dev.py migrate M14 --profile standalone
python scripts/dev.py seed M14 --scenario baseline
python scripts/dev.py check M14 --suite standalone
```

Fake Access only. **No FakePlatform** — M14 uses its actual implementation.
Real authentication and 2FA integration stay **explicitly pending** until M01
is integrated. Production RPO/RTO and full-scale load stay **PENDING**.

## B00 notes specific to this module

Owns the REAL audit/outbox and production deployment. Uses its ACTUAL
implementation, not the harness test adapter. Production deployment is covered
here; Kubernetes is NOT required.

## Human gates before this module ships

- this packet reviewed and frozen in the manifest
- every equivalence/authorisation rule reviewed before being enabled
- the phase exit gate
- first customer-facing report for each design partner, where applicable
