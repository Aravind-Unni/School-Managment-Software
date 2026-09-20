# M05 handoff

## Where things stand

Implementation is on branch `m05/assessments-grades`. Contracts are frozen at
`school-contracts-v6`. Local contracts suite and SQLite module suite are green.
Standalone PostgreSQL suite has **not** been run (no stack this session).

## Source identity

| | |
|---|---|
| Branch | `m05/assessments-grades` |
| Manifest | `school-contracts-v6` |
| Seed | baseline leaves assessment **published** (S1 scored 73.50 + confirmed v2 evidence; S2 absent) |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M05 --profile standalone
python3 scripts/dev.py migrate M05 --profile standalone
python3 scripts/dev.py seed M05 --scenario baseline
python3 scripts/dev.py check M05 --suite contracts
python3 scripts/dev.py check M05 --suite standalone
```

## Resume checklist

1. Read `docs/modules/M05/progress.md`.
2. Run standalone stack + suite; update `acceptance.json` with observed counts.
3. Open draft PR (no merge/deploy).

## PENDING integration (not freeze blockers)

- Real M12 compression / object storage reads
- Report snapshot PDF contents
- Guardian revocation mid-window
- Real M01 session / TOTP (standalone uses synthetic persona)
- Worker crash/retry for `assessment.report_snapshot` (enqueue deferred when
  `WORKER_AVAILABLE=false`; tests enable capture on FakePlatform only)
