# M14 handoff

## Where things stand

M14 platform is **implemented** on branch `m14/platform-audit-jobs-backup`.
Contracts are frozen under `school-contracts-v15`. Local SQLite module suite and
`check M14 --suite contracts` are green. Container standalone/browser suites are
**not-run** (no Docker daemon).

| Item | Value |
|---|---|
| Branch | `m14/platform-audit-jobs-backup` |
| Started from | `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`) |
| Draft PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/15 |
| Manifest | `school-contracts-v15` |

## Startup

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M14 --profile standalone
python3 scripts/dev.py migrate M14 --profile standalone
python3 scripts/dev.py seed M14 --scenario baseline
python3 scripts/dev.py check M14 --suite contracts
python3 scripts/dev.py check M14 --suite standalone
python3 scripts/dev.py check M14 --suite browser
python3 scripts/dev.py evidence M14
```

URLs come from `up` output; do not assume fixed ports.

## Fictional login (standalone)

Server-side fixed persona (localhost). Seed uses operator
`eda913d7-a893-5ecc-af4e-766d1332b2ee` for jobs/audit; company-ops
`b2222222-2222-4222-8222-2222222222c2` for restore rehearsals. Real M01 auth is
PENDING.

## Observed local results

| Suite | Result |
|---|---|
| contracts (`dev.py check M14 --suite contracts`) | green (manifest, arch, 105 shared + 9 M14) |
| module tests SQLite (`tests/modules/M14`) | 19 passed |
| frontend moduleRegistry | 11 passed |
| standalone / browser / `up` | **not-run** — Docker daemon not running |

## PENDING integration (do not claim standalone)

- Real domain job identities against other modules
- Production monitoring against live multi-module traffic
- Full-scale RPO 15m / RTO 4h validation
- Real M01 authentication / 2FA for ops identities

## Migrations

- `backend/modules/platform/migrations/0001_initial.py` — reversible create.
  No irreversible data migrations in this packet.
