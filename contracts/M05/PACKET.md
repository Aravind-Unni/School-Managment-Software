# Contract packet -- M05 assessment

Status: **FROZEN** under revision `school-contracts-v6` (reviewed 2026-09-20 by Abhinav M).

Manifest revision: `school-contracts-v6`.

---

## Artefacts in this proposal

| Artefact | Path |
|---|---|
| Review decisions (11 items) | `review-decisions.md` |
| OpenAPI | `openapi.json` |
| DTO / request schemas | `schemas/dtos.schema.json` |
| Event payloads | `schemas/events.schema.json` |
| Error rows | `error-codes.json` |
| Port signatures | `ports.md` |
| Baseline scenario | `fixtures/scenario.json` |
| Acceptance cases | `fixtures/expected-results.json` |
| Consumer response samples | `fixtures/responses.json` |

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** After review, freeze hashes in
`contracts/manifest.json`, then implement steps 1–4 (setup/marking → evidence →
publication → revisions).

## What this module must declare

A `ModuleRegistration` in `backend/modules/assessment/registration.py`:

| field | meaning |
|---|---|
| `id` | `M05` |
| `slug` | `assessment` |
| `api_prefix` | `/api/v1/assessments/` (proposed; see review item 3) |
| `frontend_routes` | setup, marking grid+viewer, missing-evidence queue, publish preview, student/guardian published view |
| `permission_codes` | `assessment.manage`, `marks.edit`, `marks.submit`, `results.approve`, `results.publish`, `results.reopen`, `evidence.view` |
| `consumers` | Access, Registry, Files (proposed), Platform, Clock |
| `scheduled_jobs` | none required for standalone; report job is on-demand enqueue |
| `migration_dependencies` | harness only in standalone |
| `health_checks` | readiness for assessment DB |

## Inherited constraints

UUID `id`, trusted `school_id`, integer `version`; `expected_version` → 409;
errors 401/403/404/409/422; cross-school is **404**; cursor pagination; UTC +
Asia/Kolkata; decimal-string marks; audit+outbox same transaction; never trust
client role/school/relationship; `ResourceGrant` never from browser.

## Standalone development (after freeze)

```bash
python scripts/dev.py up M05 --profile standalone
python scripts/dev.py migrate M05 --profile standalone
python scripts/dev.py seed M05 --scenario baseline
python scripts/dev.py check M05 --suite standalone
```

## Human gates

- this packet reviewed and frozen in the manifest
- FilesPort shared addition approved (or alternative recorded)
- no invented CBSE grade boundaries (review item 5)
- phase exit gate; first customer-facing report gate where applicable
