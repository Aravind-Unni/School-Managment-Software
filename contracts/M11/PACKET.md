# Contract packet -- M11 communications

Status: **APPROVED AND FROZEN** under revision `school-contracts-v12` on 2026-09-21
(reviewer: Abhinav M).

Manifest revision: `school-contracts-v12`.

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** Artefacts below are frozen;
a mismatch needs a reviewed contract revision.

1. OpenAPI — `openapi.json`
2. JSON Schema — `schemas/dtos.schema.json`, `schemas/events.schema.json`
3. Protocol — `ports.md` → `backend/contracts/communications.py`
4. Errors — `error-codes.json`
5. Fixtures — `fixtures/*`

## Module registration

| field | value |
|---|---|
| `id` | `M11` |
| `slug` | `communications` |
| `api_prefix` | `/api/v1/` |
| `permission_codes` | `notices.create`, `notices.publish`, `messages.send`, `messages.read_status`, `sms.configure` |
| `consumers` | access, registry, platform, clock |
| `scheduled_jobs` | deliver + reconcile |

## Standalone

```bash
python scripts/dev.py up M11 --profile standalone
python scripts/dev.py migrate M11 --profile standalone
python scripts/dev.py seed M11 --scenario baseline
python scripts/dev.py check M11 --suite standalone
```

Local/test profiles must NEVER contact a real SMS provider.
