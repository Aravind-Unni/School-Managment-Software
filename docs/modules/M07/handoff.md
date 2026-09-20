# M07 handoff

## Where things stand

Contracts for M07 are **proposed, not frozen**. Implementation has not started.
Resume on branch `m07/fees-payments-balances-receipts`.

## Source identity

| Item | Value |
|---|---|
| Branched from | `da0570c2efdd3e17ef852164d0a62a9265416fbf` |
| Manifest at branch | `school-contracts-v7` |
| Proposed freeze | `school-contracts-v8` |

## Startup (after implementation)

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

## Fictional login (standalone, after seed)

Finance persona via localhost-only fake auth (module fixture grants for
`fees.*`). Exact persona ids live in seed output / `fixture_policy.py` once
implemented. Never accept client school/role headers.

## PENDING integration (list in acceptance when implemented)

- Real M01 login / sessions / TOTP for step-up
- Real M08 transport `Fees.raise_charge` requests
- Real statements/reports against integrated Registry
- Student withdrawal does not erase debt (cross-module case)
- Worker crash/retry — N/A for M07 baseline (no broker)

## Next action for a fresh agent

1. Read `contracts/M07/review-decisions.md`
2. If not approved: stop and wait
3. If approved: freeze, then implement step 1 charge ledger
