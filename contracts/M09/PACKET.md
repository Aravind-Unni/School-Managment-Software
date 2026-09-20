# Contract packet -- M09 library

Status: **PROPOSED — awaiting human review gate.** Artefacts exist under
`contracts/M09/` but are **not** frozen in `contracts/revision.json`.

Manifest revision this packet targets: `school-contracts-v10` (proposed).
Current frozen revision remains `school-contracts-v9` until review.

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** This packet proposes:

1. OpenAPI (`openapi.json`)
2. JSON Schema for DTOs and events (`schemas/`)
3. Protocol signatures (`ports.md` → `backend/contracts/library.py` after freeze)
4. Error enums (`error-codes.json`)
5. Example fixtures (`fixtures/`)

Review decisions: [`review-decisions.md`](review-decisions.md).

## What this module must declare

A `ModuleRegistration` in `backend/modules/library/registration.py`:

| field | meaning |
|---|---|
| `id` | `M09` |
| `slug` | `library` |
| `api_prefix` | `/api/v1/` |
| `frontend_routes` | Catalogue, issue desk, overdues, borrower history |
| `permission_codes` | `library.catalogue.manage`, `library.issue`, `library.return`, `library.renew`, `library.read_overdues`, `library.read_own` |
| `consumers` | `access`, `registry`, `platform`, `clock` |
| `scheduled_jobs` | none in baseline (overdue detection on GET) |
| `migration_dependencies` | none |
| `health_checks` | `library_tables` |

## Inherited, non-negotiable constraints

- UUID `id`, trusted `school_id`, integer `version` on mutable aggregates
- `expected_version` on every update; stale means **409**
- errors use the frozen envelope: 401 / 403 / 404 / 409 / 422
- **cross-school access is 404, never 403**
- collections return `items` + `next_cursor`
- UTC instants, Asia/Kolkata civil dates
- audit + outbox in the **same transaction** as the write
- Access checks on API, service, workers, exports and private files
- client role, school and relationship claims are never trusted
- No library fines / money balances

## Standalone development

```bash
python scripts/dev.py up M09 --profile standalone
python scripts/dev.py migrate M09 --profile standalone
python scripts/dev.py seed M09 --scenario baseline
python scripts/dev.py check M09 --suite standalone
```

Dependency ports bind to deterministic fakes. Real authentication/2FA and
real Registry contact fields stay **explicitly pending**.

## Human gates before this module ships

- this packet reviewed and frozen in the manifest
- every authorisation rule reviewed before being enabled
- the phase exit gate
- first customer-facing report for each design partner, where applicable
