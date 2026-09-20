# M07 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting PostgreSQL/browser evidence |
| Status | Contracts frozen + implemented. **STANDALONE_VERIFIED=false** (Docker not run this session). |
| Branch | `m07/fees-payments-balances-receipts` |
| Started from | `da0570c2efdd3e17ef852164d0a62a9265416fbf` (`origin/main`) |
| Manifest revision | `school-contracts-v8` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/8 (draft) |
| Head commit | `253d7f1d6af5c3e8491957b675c9e0b3d1662921` |
| Last recorded | 2026-09-20 |

## Original request

Build M07 fees, payments, balances and receipts as an independently runnable
standalone module. Contracts first; then implement. May commit/push/draft PR;
no merge/deploy.

## Completed behavior

- Contracts approved and frozen (`school-contracts-v8`): OpenAPI, DTO/event
  schemas, error rows, FeesPort, fixtures.
- Shared `FeesPort` + fee DTOs in `backend/contracts/fees.py`.
- Backend: fee plans, charges (`source_key`), payments (idempotency + receipts),
  allocations with locks, concessions, refunds, reversals (2FA), statements,
  overdue list, daily collections.
- Frontend: setup, statement, collect, receipt, overdue, concessions (en+ml).
- Seeds: baseline tuition 100000 + opening 25000 + bus 30000 for S1.
- Acceptance: 21 tests in `tests/modules/M07/`.

## Incomplete / not-run

- Standalone PostgreSQL suite — not run this session (use `dev.py up`).
- Browser suite — not-run.
- PENDING integration: real M01 2FA, real M08 transport charges, integrated
  statements/reports, withdrawal preserves debt.

## Test numbers observed

```
check M07 --suite contracts → PASS (manifest, arch 7, shared 105, M07 contract 6)
MODULE_ID=M07 pytest tests/modules/M07 (test_sqlite) → 21 passed
frontend vitest → 65 passed
check M07 --suite standalone → not-run
check M07 --suite browser → not-run
```

## Exact next step

1. `python3 scripts/dev.py up M07 --profile standalone`
2. migrate + seed baseline; `check M07 --suite standalone`
3. `check M07 --suite browser` if Playwright available
4. `evidence M07`; set STANDALONE_VERIFIED only after peer verify from fresh checkout
