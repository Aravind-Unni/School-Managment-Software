# Contract packet -- M07 fees

Status: **FROZEN** under `school-contracts-v8`.

Review: [`review-decisions.md`](review-decisions.md) — items 1–12 approved
2026-09-20 by Abhinav M.

---

## Artefacts

1. OpenAPI — [`openapi.json`](openapi.json)
2. JSON Schema — [`schemas/dtos.schema.json`](schemas/dtos.schema.json),
   [`schemas/events.schema.json`](schemas/events.schema.json)
3. Protocol signatures — [`ports.md`](ports.md) (`FeesPort`)
4. Error enums — [`error-codes.json`](error-codes.json)
5. Example fixtures — [`fixtures/`](fixtures/)

## Module registration

| field | value |
|---|---|
| `id` | `M07` |
| `slug` | `fees` |
| `api_prefix` | `/api/v1/` |
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
