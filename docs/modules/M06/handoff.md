# M06 handoff

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M06 --profile standalone
python3 scripts/dev.py migrate M06 --profile standalone
python3 scripts/dev.py seed M06 --scenario baseline
```

Use printed URLs from `up` (ports are dynamic).

## Fictional login (standalone)

Fixed persona mode (localhost only). Default: Teacher T1 with recent 2FA.
Switch personas only via server-side DEV_PERSONA — never client headers.

## Manual actions / expected outcomes

1. Open student progress → S1 overall mean **65.00**, attendance **80.00**,
   topic **insufficient data**, one open low-attendance warning.
2. Open S2 → metrics labeled insufficient/incomplete; no invented values.
3. As G2 → S1 dashboard → **404**.
4. As G1 → export → no restricted observation body.
5. Dismiss warning with reason → state dismissed; history retained.
6. Rebuild → S1 metrics unchanged at 65 / 80.

## Migrations

- `backend/modules/performance/migrations/0001_initial.py` — reversible create.
- Irreversible: none in this release.

## Commands / results (this session)

| Command | Result |
|---|---|
| `check M06 --suite contracts` | PASS |
| `MODULE_ID=M06 pytest tests/modules/M06` | 19 passed |
| frontend vitest | 65 passed |
| `check M06 --suite standalone` | not-run |
| `check M06 --suite browser` | not-run |

## Identities

| Item | Value |
|---|---|
| Branch | `m06/analytics-warnings-interventions` |
| Started from | `abe35b7c4621df8b6ebf111293401e80b4b255a1` |
| Contract revision | `school-contracts-v7` |

## PENDING integration tests

- Rebuild/reconciliation from real Assessment (M05) and Attendance (M04) providers.
- Comparable grading policy comparisons with school-approved scales.
- Real M01 authentication / 2FA.
- Worker crash/retry against real broker (eager mode must not claim coverage).
