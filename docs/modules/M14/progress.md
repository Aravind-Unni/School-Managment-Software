# M14 progress

| | |
|---|---|
| Phase | Implementation (steps 1–4 complete locally; container path pending) |
| Status | Contracts frozen; module implemented; contracts suite green |
| Branch | `m14/platform-audit-jobs-backup` |
| Branched from | `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`) |
| Manifest revision | `school-contracts-v15` (M14 frozen) |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/15 (draft) |
| Tip | `25c7541c4ee13b124daba8e3b44fff660a670d5c` |
| Last recorded | 2026-09-21 |

## Original request

Build M14 Audit / jobs / deployment / backup / observability as an independently
runnable standalone profile. Propose contracts, freeze, implement, test. Delivery
may commit, push, and open a draft PR; do not merge or deploy.

## Completed behaviour

- Contract packet reviewed and frozen under `school-contracts-v15` (items 1–16
  approved as proposed).
- Real `PlatformAdapter` (audit/outbox/jobs tables); no TestPlatformAdapter for
  M14 (bound via settings `overrides`).
- REST: `health/live`, `health/ready`, `jobs/{id}`, `jobs/{id}/retry`, `audit`,
  `operations/restore-rehearsals`.
- Outbox dispatch + sample consumer with `(consumer, event_id)` dedupe.
- Restore rehearsals: ops identity, production target forbidden, hash/fee checks.
- Frontend operator jobs / audit / backups pages (en + ml).
- Registration, seeds, migrations, fixture Access grants, CI sentinels.

## Incomplete behaviour / evidence

- `dev.py up M14` / standalone suite / browser suite: **not-run** — Docker daemon
  absent on this machine (`doctor` reports it).
- Worker crash/retry against real broker: not claimed (eager refuses honestly).
- PENDING integration: real domain job identities, production monitoring,
  full-scale RPO/RTO, real M01 auth/2FA.
- STANDALONE_VERIFIED not recorded.

## Changed interfaces

- Frozen M14 contracts (OpenAPI, DTOs, events, errors, fixtures).
- `build_fake_registry(..., overrides=)` for profile-supplied real platform.
- `dev/modules/M14/module.json` requires object_storage.

## Exact next step

1. Start Docker; `python3 scripts/dev.py up M14 --profile standalone` then
   migrate / seed / check standalone + browser / evidence.
2. Second-developer verification from a fresh checkout before STANDALONE_VERIFIED.
3. Merge only after peer review of the draft PR.

## Blockers

- Container engine not running on the author machine (honest not-run).
- PENDING items above remain until Section C.
