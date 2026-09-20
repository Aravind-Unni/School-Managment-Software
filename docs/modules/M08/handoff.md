# M08 handoff

## Where things stand

M08 transport is implemented on branch
`m08/bus-participation-fee-coordination`. Contracts frozen under
`school-contracts-v9`. Local SQLite module tests and contracts suite are the
verification target for this session. Standalone PostgreSQL and browser suites
not run.

## Source identity

| Item | Value |
|---|---|
| Branched from | `6b6aef011b5f428b3d45ed0cd6761cfa88df8707` |
| Manifest | `school-contracts-v9` |
| Draft PR | not opened |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M08 --profile standalone
python3 scripts/dev.py migrate M08 --profile standalone
python3 scripts/dev.py seed M08 --scenario baseline
python3 scripts/dev.py check M08 --suite contracts
python3 scripts/dev.py check M08 --suite standalone
python3 scripts/dev.py check M08 --suite browser
python3 scripts/dev.py evidence M08
python3 scripts/dev.py down M08
```

## Fictional login (standalone)

Transport persona: `PRINCIPAL_P1` via localhost-only fake auth with fixture
grants for `transport.*`. G1 may read S1 participation; G2 gets 404 on S1.
Never accept client school/role headers.

## Manual smoke after seed

1. GET `/api/v1/bus-participants?date=2026-06-15` → S1 present, S2 absent.
2. POST `/api/v1/bus-billing-runs` `{"period":"2026-06","policy_version":1}` →
   one 50000 paise charge for S1 via FakeFees.
3. Arm timeout in tests: retry recovers charge_id without a second charge.
4. As G2: GET S1 participation → 404.

## PENDING integration

- real_m01_auth_2fa
- real_m07_fees_ledger
- gps_routes_out_of_scope

## Next action for a fresh agent

1. Confirm contracts + SQLite suites green
2. Start Docker; run standalone + browser suites
3. Update evidence and acceptance.json with observed results
