# M04 handoff — teacher attendance

## How to run

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M04 --profile standalone
python3 scripts/dev.py migrate M04 --profile standalone
python3 scripts/dev.py seed M04 --scenario baseline
python3 scripts/dev.py check M04 --suite contracts
python3 scripts/dev.py check M04 --suite standalone
python3 scripts/dev.py check M04 --suite browser
python3 scripts/dev.py evidence M04
python3 scripts/dev.py down M04
```

Use the URLs printed by `up`. Ports are dynamic.

## Fictional login (standalone)

No real login. Loopback fixed persona is **T1** (class teacher of C1) with
2FA. Switch personas only via server settings in tests — never via headers.

Baseline date: **2026-07-15**. P1 Maths (T1), P2 English (T2, substitute T3).

## Expected seed outcomes

- P1 submitted: S1 present, S2 absent, S3 present; P2 unopened.
- Summaries: S1/S2 eligible=2 marked=1 unmarked=1; S3 eligible=1.

## PENDING integration (do not claim passed)

1. Real Registry roster transfers
2. Real Timetable substitutions (vs FakeTimetable)
3. Notifications / SMS consumers
4. Performance module denominators using Attendance.get_summary

## Contract identity

- Revision: `school-contracts-v5`
- M04 frozen 2026-09-20 by Abhinav M
- Events: `attendance.submitted`, `attendance.corrected`
