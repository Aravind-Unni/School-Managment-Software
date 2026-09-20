# Contract packet -- M10 alumni

Status: **APPROVED AND FROZEN** under revision `school-contracts-v11` on 2026-09-21
(see `review-decisions.md`).

Manifest revision: `school-contracts-v11`.

Artefacts: `openapi.json`, `schemas/dtos.schema.json`, `schemas/events.schema.json`,
`error-codes.json`, `ports.md`, `review-decisions.md`, fixtures under `fixtures/`.

Shared port: `backend/contracts/alumni.py` (`AlumniPort`).

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** Consumer suites assert against
the frozen fixtures. A mismatch needs a reviewed contract revision.

## What this module must declare

A `ModuleRegistration` in `backend/modules/alumni/registration.py`:

| field | meaning |
|---|---|
| `id` | `M10` |
| `slug` | `alumni` |
| `api_prefix` | `/api/v1/` |
| `api_path_roots` | `alumni/` |
| `frontend_routes` | candidates, directory, profile/contact, export |
| `permission_codes` | `alumni.review`, `alumni.manage`, `alumni.read`, `alumni.export`, `alumni.contact_self` |
| `consumers` | Access, Registry, Platform, Clock |
| `scheduled_jobs` | none in baseline |
| `migration_dependencies` | none beyond harness |
| `health_checks` | readiness probe |

## Inherited constraints

UUID `id`, trusted `school_id`, integer `version`; `expected_version` → 409;
errors 401/403/404/409/422; cross-school **404**; `items`+`next_cursor`;
UTC / Asia/Kolkata; audit+outbox same transaction; never trust client claims.

## Standalone development

```bash
python scripts/dev.py up M10 --profile standalone
python scripts/dev.py migrate M10 --profile standalone
python scripts/dev.py seed M10 --scenario baseline
python scripts/dev.py check M10 --suite standalone
```

## Human gates

- packet reviewed and frozen (done — see `review-decisions.md`)
- real auth/2FA, StudentLeft, exchange exports remain PENDING until Section C
