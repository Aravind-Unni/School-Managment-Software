# M07 handoff

## Where things stand

M07 fees is implemented on branch `m07/fees-payments-balances-receipts`.
Contracts frozen under `school-contracts-v8`. Local SQLite module tests and
contracts suite are green. Standalone PostgreSQL and browser suites not run.

## Source identity

| Item | Value |
|---|---|
| Branched from | `da0570c2efdd3e17ef852164d0a62a9265416fbf` |
| Manifest | `school-contracts-v8` |
| Draft PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/8 |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M07 --profile standalone
python3 scripts/dev.py migrate M07 --profile standalone
python3 scripts/dev.py seed M07 --scenario baseline
python3 scripts/dev.py check M07 --suite contracts
python3 scripts/dev.py check M07 --suite standalone
python3 scripts/dev.py check M07 --suite browser
python3 scripts/dev.py evidence M07
python3 scripts/dev.py down M07
```

URLs: use `up` output; do not assume fixed ports.

## Fictional login (standalone)

Finance persona: `PRINCIPAL_P1` via localhost-only fake auth with fixture grants
for `fees.*`. Guardians G1/G2 for statement visibility tests. Never accept
client school/role headers.

## Manual smoke after seed

1. As finance: GET `/api/v1/students/{S1}/fee-statement` → charged_paise 155000.
2. POST `/api/v1/payments` with Idempotency-Key, allocate 40000 to tuition →
   charge balance 60000; retry same key → same receipt.
3. POST concession 10000 → charge balance 50000.
4. As G2: GET S1 statement → 404.

## PENDING integration

- real_m01_auth_2fa
- real_m08_transport_charges
- integrated_statements_reports
- withdrawal_preserves_debt

## Next action for a fresh agent

1. Start Docker; run standalone + browser suites
2. Update evidence and acceptance.json with observed results
3. Peer verify from fresh checkout before STANDALONE_VERIFIED
