# Contract packet -- M08 transport

Status: **FROZEN** under `school-contracts-v9` (see `review-decisions.md`).

Manifest revision this packet targets: `school-contracts-v9`

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** This packet contains:

1. OpenAPI (`openapi.json`)
2. JSON Schema for DTOs and events (`schemas/`)
3. Protocol signatures (`ports.md` → `backend/contracts/transport.py`)
4. Error enums (`error-codes.json`)
5. Example fixtures (`fixtures/`)

Those are hashed in `contracts/manifest.json`. A mismatch needs a reviewed
contract revision.

## What this module must declare

A `ModuleRegistration` in `backend/modules/transport/registration.py`:

| field | meaning |
|---|---|
| `id` | `M08` |
| `slug` | `transport` |
| `api_prefix` | `/api/v1/` |
| `frontend_routes` | React routes with nav metadata and required permission |
| `permission_codes` | `transport.manage`, `transport.read`, `transport.bill` |
| `consumers` | `access`, `registry`, `fees`, `platform`, `clock` |
| `scheduled_jobs` | none in baseline (billing runs are on-demand jobs) |
| `migration_dependencies` | none |
| `health_checks` | `transport_tables` |

## Inherited, non-negotiable constraints

- UUID `id`, trusted `school_id`, integer `version` on mutable aggregates
- `expected_version` on every update; stale means **409**
- errors use the frozen envelope: 401 / 403 / 404 / 409 / 422
- **cross-school access is 404, never 403**
- collections return `items` + `next_cursor`
- UTC instants, Asia/Kolkata civil dates, integer INR paise
- audit + outbox in the **same transaction** as the write
- Access checks on API, service, workers, exports and private files
- client role, school and relationship claims are never trusted

## Standalone development

```bash
python scripts/dev.py up M08 --profile standalone
python scripts/dev.py migrate M08 --profile standalone
python scripts/dev.py seed M08 --scenario baseline
python scripts/dev.py check M08 --suite standalone
```

Dependency ports bind to deterministic fakes (including FakeFees). Real
authentication/2FA and real Fees ledger stay **explicitly pending**.

## B00 notes specific to this module

No GPS, routes, tracking hardware, telemetry or vehicle-maintenance subsystem.

## Human gates before this module ships

- this packet reviewed and frozen in the manifest
- every authorisation rule reviewed before being enabled
- the phase exit gate
- first customer-facing report for each design partner, where applicable
