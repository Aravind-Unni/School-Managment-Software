# Contract packet -- M11 communications

Status: **PROPOSED FOR REVIEW**. Artefacts exist under `contracts/M11/`; not
frozen in `contracts/manifest.json` until items in `review-decisions.md` are
approved.

Manifest revision this packet targets: `school-contracts-v12` (proposed;
current reviewed revision remains `school-contracts-v11`).

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** Review must approve:

1. OpenAPI — `openapi.json`
2. JSON Schema — `schemas/dtos.schema.json`, `schemas/events.schema.json`
3. Protocol signatures — `ports.md` → `backend/contracts/communications.py` after freeze
4. Error enums — `error-codes.json`
5. Example fixtures — `fixtures/*`

Then freeze hashes in `contracts/manifest.json` / `revision.json`. Only then
implement.

## What this module must declare

A `ModuleRegistration` in `backend/modules/communications/registration.py`:

| field | meaning |
|---|---|
| `id` | `M11` |
| `slug` | `communications` |
| `api_prefix` | `/api/v1/` (operations under notices/messages/deliveries/sms) |
| `frontend_routes` | composer, templates, delivery dashboard |
| `permission_codes` | `notices.create`, `notices.publish`, `messages.send`, `messages.read_status`, `sms.configure` |
| `consumers` | access, registry, platform, clock |
| `scheduled_jobs` | deliver + reconcile workers |
| `migration_dependencies` | none beyond foundation harness |
| `health_checks` | readiness for DB + broker when profile includes worker |

## Inherited, non-negotiable constraints

Same as foundation: UUID id, trusted school_id, integer version, expected_version
→ 409, error envelope, cross-school 404, cursor collections, UTC + Asia/Kolkata,
audit+outbox same transaction, never trust client role/school/relationship.

## Standalone development (after freeze)

```bash
python scripts/dev.py up M11 --profile standalone
python scripts/dev.py migrate M11 --profile standalone
python scripts/dev.py seed M11 --scenario baseline
python scripts/dev.py check M11 --suite standalone
```

Local/test profiles must NEVER contact a real SMS provider.

## Human gates

- this packet reviewed and frozen
- real provider sandbox before production SMS
- phase exit gate
