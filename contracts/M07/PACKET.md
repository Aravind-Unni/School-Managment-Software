# Contract packet -- M07 fees

Status: **PROPOSED**. Artefacts exist under `contracts/M07/` and await human
review before freeze. Do not implement against these as frozen until
`contracts/revision.json` lists M07 and `manifest.json` status is `frozen`.

Manifest revision this packet targets: `school-contracts-v8` (proposed next
revision after current `school-contracts-v7`).

Review checklist: [`review-decisions.md`](review-decisions.md).

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** This packet proposes:

1. OpenAPI — [`openapi.json`](openapi.json)
2. JSON Schema — [`schemas/dtos.schema.json`](schemas/dtos.schema.json),
   [`schemas/events.schema.json`](schemas/events.schema.json)
3. Protocol signatures — [`ports.md`](ports.md) (`FeesPort`)
4. Error enums — [`error-codes.json`](error-codes.json)
5. Example fixtures — [`fixtures/`](fixtures/)

Those are frozen in `contracts/manifest.json` only after review.

## What this module must declare

A `ModuleRegistration` in `backend/modules/fees/registration.py`:

| field | meaning |
|---|---|
| `id` | `M07` |
| `slug` | `fees` |
| `api_prefix` | `/api/v1/` |
| `api_path_roots` | `fee-plans/`, `charges/`, `payments/`, `concessions/`, `refunds/`, `students/`, `fees/` |
| `frontend_routes` | setup, statement, collection, receipt, overdue, concessions, reversal |
| `permission_codes` | `fees.configure`, `fees.read`, `fees.record_payment`, `fees.concede`, `fees.reverse_payment`, `fees.refund` |
| `consumers` | `access`, `registry`, `platform`, `clock` |
| `scheduled_jobs` | none in baseline |
| `migration_dependencies` | none |
| `health_checks` | fees tables readiness |

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
python scripts/dev.py up M07 --profile standalone
python scripts/dev.py migrate M07 --profile standalone
python scripts/dev.py seed M07 --scenario baseline
python scripts/dev.py check M07 --suite standalone
```

Dependency ports bind to deterministic fakes. Real authentication and 2FA
integration stay **explicitly pending** until M01 is integrated.

## B00 notes specific to this module

Money is integer INR paise. No full accounting and no payroll are in scope.
No online payment gateway. Bus/library charges use this ledger via `FeesPort`.

## Human gates before this module ships

- this packet reviewed and frozen in the manifest
- late-fee / bus-proration / concession-authority policy examples signed
- the phase exit gate
- first customer-facing report for each design partner, where applicable
