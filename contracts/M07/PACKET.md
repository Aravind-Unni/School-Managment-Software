# Contract packet -- M07 fees

Status: **APPROVED AND FROZEN** under revision `school-contracts-v8` on 2026-09-20
by Abhinav M. Artefacts live under `contracts/M07/`.

Manifest revision: `school-contracts-v8`.

Review: [`review-decisions.md`](review-decisions.md) — items 1–12 approved
2026-09-20 by Abhinav M.

---

## Artefacts (frozen)

| Artefact | Path |
|---|---|
| Review decisions (12 items) | `review-decisions.md` |
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
| `id` | `M07` |
| `slug` | `fees` |
| `api_prefix` | `/api/v1/` |
| `api_path_roots` | `fee-plans/`, `charges/`, `payments/`, `concessions/`, `refunds/`, `students/`, `fees/` |
| `permission_codes` | `fees.configure`, `fees.read`, `fees.record_payment`, `fees.concede`, `fees.reverse_payment`, `fees.refund` |
| `consumers` | `access`, `registry`, `platform`, `clock` |

## Standalone

```bash
python scripts/dev.py up M07 --profile standalone
python scripts/dev.py migrate M07 --profile standalone
python scripts/dev.py seed M07 --scenario baseline
python scripts/dev.py check M07 --suite standalone
```

Money is integer INR paise. No gateway, payroll, or full accounting.
