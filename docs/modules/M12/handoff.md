# M12 handoff

## State

Contracts **frozen** under `school-contracts-v13`. Module implemented on
`m12/compressed-answer-sheet-files`. Local SQLite module tests (22) and
contracts suite green this session. Standalone PostgreSQL + browser
**not-run**.

| | |
|---|---|
| Branch | `m12/compressed-answer-sheet-files` |
| Started from | `c3ece552164f4d7b99c8f688903f3892ecfeaeac` (`origin/main`) |
| Manifest | `school-contracts-v13` |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M12 --profile standalone
python3 scripts/dev.py migrate M12 --profile standalone
python3 scripts/dev.py seed M12 --scenario baseline
```

Fixed synthetic persona (uploader/reviewer = TEACHER_T1). Object store is
in-memory unless `OBJECT_STORAGE_*` is set (MinIO in Compose).

## Expected outcomes (baseline)

- FilesPolicy economical fixture (7-day grace, 12MB/page, 40MP).
- ≥10 seeded synthetic answer-sheet pages; contracted candidate / accepted /
  hold ids; School B foreign file for isolation.
- Animated/malformed decode → rejected + `files.rejected`.
- Pin immutable; purge blocked when unreviewed / unverified / hold.
- Cross-school status → 404.

## Migrations

- `modules/files/migrations/0001_initial.py` — reversible CreateModel set.

## PENDING integration

- Real M01 auth/2FA for `files.retention.manage`.
- Assessment publication gates for parent reads.
- Independent backup restoration verifier (fake only today).
- Production object lifecycle / MinIO retention rules.
