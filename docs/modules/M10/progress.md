# M10 alumni — progress

| | |
|---|---|
| Phase | Implementation complete; awaiting standalone PostgreSQL + browser evidence |
| Status | Contracts **frozen** under `school-contracts-v11`. Module code on branch. |
| Branch | `m10/alumni-records-contact-permissions` |
| Started from | `3ae3f8cbc25e09d04cb9a409411072cd6fd9a1bc` (`origin/main`) |
| Manifest revision | `school-contracts-v11` |
| Last recorded | 2026-09-21 |

## Original request

BEGIN M10 alumni records and contact permissions — independent standalone
module, contracts first, then implement/test; may commit/push/draft PR; no merge.

## Completed behaviour

- Contracts frozen (`school-contracts-v11`): OpenAPI, DTO/event schemas, error
  rows, AlumniPort, fixtures; items 1–14 approved.
- Alumni Django app: AlumniPolicy, AlumniCandidate, AlumniProfile,
  ContactPreference, ContactAmendment
- API: candidates list/approve, directory, contact patch, exports (202)
- Idempotent create_candidate; transfer stays pending when policy null;
  preference withdrawal + `is_selectable_for_contact`; export field grants;
  audit+outbox in same transaction
- Frontend feature module (candidates, directory, profile, export) en/ml
- Seeds baseline from `contracts/M10/fixtures/scenario.json`

## Verified this session

```
python3 scripts/dev.py check M10 --suite contracts  → pass
  (manifest ok, arch_check 7/7, shared 105, M10 contract 8)
MODULE_ID=M10 pytest tests/modules/M10              → 19 passed
frontend vitest moduleRegistry.test.ts              → 11 passed
```

Standalone / browser: **not-run** (no running Compose stack). STANDALONE_VERIFIED=false.

## Incomplete / PENDING integration

- Standalone PostgreSQL suite + browser suite
- real_student_left_ingestion
- real_account_lifecycle (Access)
- exchange_export_delivery (M13)
- real_m01_auth_2fa

## Exact next step

1. `python3 scripts/dev.py up M10 --profile standalone` (Docker)
2. migrate + seed; `check M10 --suite standalone` / browser
3. `evidence M10`; set STANDALONE_VERIFIED only after peer verify from fresh checkout
