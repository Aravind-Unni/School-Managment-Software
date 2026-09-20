# M09 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting standalone PostgreSQL + browser evidence |
| Status | Contracts **frozen** under `school-contracts-v10`. Module code on branch. |
| Branch | `m09/library-catalogue-lending` |
| Started from | `b046ad6e567e3a1e6d165d17ffd101c3821300be` (`origin/main`) |
| Manifest revision | `school-contracts-v10` |
| PR | (draft, pending push) |
| Head commit | (see git) |
| Last recorded | 2026-09-21 |

## Original request

Build M09 library catalogue lending and returns as an independently runnable
standalone module. Contracts first; then implement. May commit/push/draft PR;
no merge/deploy.

## Completed behaviour

- Contracts frozen (`school-contracts-v10`): OpenAPI, DTO/event schemas, error
  rows, LibraryPort, fixtures; items 1–18 approved.
- Library Django app: Title, Copy, Loan, Renewal, CopyAdjustment, policy,
  issue idempotency
- API per OpenAPI; concurrent issue conflict; retry-safe return; renewals;
  overdues on GET; catalogue import review; borrower history isolation
- Frontend feature module (catalogue, desk, overdues) en/ml
- Seeds baseline: one Malayalam title, ACC-1001, S1/S2 borrowers

## Verified this session

```
python3 scripts/dev.py check M09 --suite contracts  → pass
MODULE_ID=M09 pytest tests/modules/M09              → 17 passed
frontend vitest moduleRegistry.test.ts              → 11 passed
```

Standalone / browser: **not-run**. STANDALONE_VERIFIED=false.

## Incomplete / PENDING integration

- Standalone PostgreSQL suite + browser suite
- real_m01_auth_2fa
- real_m02_registry_borrower_contacts
- library_fines_out_of_scope (Fees later)

## Exact next step

1. Push branch; open draft PR
2. `python3 scripts/dev.py up M09 --profile standalone` (Docker)
3. migrate + seed; `check M09 --suite standalone` / browser
4. `evidence M09`; set STANDALONE_VERIFIED only after peer verify from fresh checkout
