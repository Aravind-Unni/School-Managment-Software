# M13 handoff

## State

Contracts **frozen** under `school-contracts-v14`. Module implemented on
`m13/reports-imports-exports`. Local SQLite module tests (**47**) and contracts
suite green this session. Standalone PostgreSQL + browser **not-run** (no
container engine).

| | |
|---|---|
| Branch | `m13/reports-imports-exports` |
| Started from | `3d0b03bbae4d7509ec5c27ef8e4a029d4eebdf13` (`origin/main`) |
| Manifest | `school-contracts-v14` |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M13 --profile standalone
python3 scripts/dev.py migrate M13 --profile standalone
python3 scripts/dev.py seed M13 --scenario baseline
```

Use the printed URLs from `up` (ports are dynamic). Fixed synthetic persona is
principal P1 (`DEV_PERSONA` in standalone). Fake Access / Registry / Assessment /
Attendance / Fees / Files / Platform only.

## Fictional login

Standalone uses a server-derived fixed persona — no password form. Switch actor
in tests via `as_persona`. Baseline grants staff import/export/report-card
actions to P1; guardian G2 is unrelated and must be denied artifact download.

## Expected outcomes (baseline)

- Enrolments CSV: duplicate + malformed rows reported; formula cell neutralized.
- Commit requires matching `source_digest`; wrong digest → 409.
- Same Idempotency-Key replay after apply → 202, no second `apply_rows`.
- Export CSV formula cells escaped; forbidden fields omitted.
- Report card PDF contains Malayalam (`മലയാളം`); snapshot revision IDs stable
  after a later policy version seed change; supersede links old→new.
- Cross-school job ids → 404.

## Migrations

- `modules/exchange/migrations/0001_initial.py` — reversible CreateModel set.
  No irreversible data migrations.

## Commands / results (this session)

```text
python3 scripts/contract_manifest.py --check   # OK school-contracts-v14
python3 scripts/arch_check.py                  # OK 7 checks
MODULE_ID=M13 … pytest tests/modules/M13       # 47 passed
python3 scripts/dev.py check M13 --suite contracts  # pass
python3 scripts/dev.py check M13 --suite standalone # not-run (no stack)
```

## PENDING integration

- Real domain adapters (Registry/Assessment/Fees/Library apply paths).
- Opening-balance / loans reconciliation against signed source totals.
- Real artifact ACLs via M12 production FilesPort.
- Real M01 auth/2FA.
- Standalone PostgreSQL + worker crash/retry + browser (both locales).

## Open questions

- Enrolments formula cell in `effective_from` is neutralized then also fails
  date grammar (recorded as row error). Product may prefer a dedicated
  `formula_cell` warning instead; not invented here.
