# M08 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting standalone PostgreSQL + browser evidence |
| Status | Contracts **frozen** under `school-contracts-v9`. Module code on branch. |
| Branch | `m08/bus-participation-fee-coordination` |
| Started from | `6b6aef011b5f428b3d45ed0cd6761cfa88df8707` (`origin/main`) |
| Manifest revision | `school-contracts-v9` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/9 (draft) |
| Head commit | `a57b9fbf30e12e6a286451a0fc3660940d4c2334` |
| Last recorded | 2026-09-21 |

## Original request

Build M08 bus participation and fee coordination as an independently runnable
standalone module. Contracts first; then implement. May commit/push/draft PR;
no merge/deploy.

## Completed behaviour

- Contracts frozen (`school-contracts-v9`): OpenAPI, DTO/event schemas, error
  rows, TransportPort, fixtures; items 1–12 approved.
- FakeFees harness: source_key dedupe, commit-then-timeout, M08 plan seed
- Transport Django app: Bus, Participation, BillingRequest, AdjustmentRequest
- API per OpenAPI; overlap reject; version conflict; audit + events
- Billing run enqueue with EagerModeNotAsserted → sync process
- Partial month without proration → blocked; retry recovers lost charge link
- Frontend feature module registered; seeds baseline S1 in / S2 out

## Verified this session

```
python3 scripts/dev.py check M08 --suite contracts  → pass (105 shared + 7 M08)
MODULE_ID=M08 pytest tests/modules/M08              → 18 passed
frontend vitest moduleRegistry.test.ts              → 11 passed
```

Standalone / browser: **not-run**. STANDALONE_VERIFIED=false.

## Incomplete / PENDING integration

- Standalone PostgreSQL suite + browser suite
- real_m01_auth_2fa
- real_m07_fees_ledger (replace FakeFees)

## Exact next step

1. `python3 scripts/dev.py up M08 --profile standalone` (Docker)
2. migrate + seed; `check M08 --suite standalone` / browser
3. `evidence M08`; set STANDALONE_VERIFIED only after peer verify from fresh checkout
