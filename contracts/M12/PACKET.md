# Contract packet -- M12 files

Status: **APPROVED AND FROZEN** under revision `school-contracts-v13` on 2026-09-21
(reviewer: Abhinav M).

Manifest revision: `school-contracts-v13`.

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** Artefacts below are frozen;
a mismatch needs a reviewed contract revision.

1. OpenAPI — `openapi.json`
2. JSON Schema — `schemas/dtos.schema.json`, `schemas/events.schema.json`
3. Protocol — `ports.md` → existing `backend/contracts/ports.py` `FilesPort`
4. Errors — `error-codes.json`
5. Fixtures — `fixtures/*`

## Module registration

| field | value |
|---|---|
| `id` | `M12` |
| `slug` | `files` |
| `api_prefix` | `/api/v1/` |
| `permission_codes` | `files.upload`, `files.review_quality`, `files.read`, `files.retention.manage` |
| `consumers` | access, platform, clock |
| `scheduled_jobs` | orphan upload cleanup; economical source purge |

## Standalone

```bash
python scripts/dev.py up M12 --profile standalone
python scripts/dev.py migrate M12 --profile standalone
python scripts/dev.py seed M12 --scenario baseline
python scripts/dev.py check M12 --suite standalone
```

Real image decode/compress and module-owned S3-compatible storage (MinIO when
Compose is up). Access and Platform stay deterministic fakes. Real M01 auth/2FA
and Assessment publication gates stay **PENDING**.
