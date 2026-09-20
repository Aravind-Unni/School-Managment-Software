# Contract packet -- M06 performance

Status: **APPROVED AND FROZEN** under revision `school-contracts-v7` on 2026-09-20
by Abhinav M. Artefacts live under `contracts/M06/`.

Manifest revision: `school-contracts-v7`.

---

## Artefacts (frozen)

| Artefact | Path |
|---|---|
| Review decisions (10 items) | `review-decisions.md` |
| OpenAPI | `openapi.json` |
| DTO schemas | `schemas/dtos.schema.json` |
| Event schemas | `schemas/events.schema.json` |
| Error rows | `error-codes.json` |
| Port signatures | `ports.md` |
| Consumer fixtures | `fixtures/*.json` |

---

## ModuleRegistration

| field | value |
|---|---|
| `id` | `M06` |
| `slug` | `performance` |
| `api_prefix` | `/api/v1/` |
| `api_path_roots` | `performance/`, `warning-rules/`, `warnings/`, `interventions/`, `meetings/` |
| `permission_codes` | `performance.read`, `warnings.manage`, `interventions.manage`, `meetings.record`, `observations.read_sensitive` |
| `consumers` | `access`, `registry`, `assessment`, `attendance`, `platform`, `clock` |
| `scheduled_jobs` | `performance.reconcile_projections` (Asia/Kolkata daily) |
| `migration_dependencies` | `()` |

---

## Inherited constraints

UUID `id`, trusted `school_id`, integer `version` on mutable aggregates;
`expected_version` → 409; errors 401/403/404/409/422; cross-school is **404**;
collections `items` + `next_cursor`; UTC / Asia/Kolkata / paise / decimal-string
marks; audit + outbox in the same transaction; never trust client role/school/
relationship; Access on API, service, workers, exports.

---

## Standalone

```bash
python scripts/dev.py up M06 --profile standalone
python scripts/dev.py migrate M06 --profile standalone
python scripts/dev.py seed M06 --scenario baseline
python scripts/dev.py check M06 --suite standalone
```

Fake Assessment / Attendance / Registry / Access / Platform. Real PostgreSQL,
real broker/worker for projection rebuild. Real auth/2FA pending M01
integration.

## B00 notes

Reads from assessment and attendance via ports. Topic analysis requires tagged
item data; otherwise `insufficient_data`. Forecasting history is out of scope
for M06 (pooled aggregates belong elsewhere).
