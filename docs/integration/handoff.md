# Integration handoff — C02

Read [`progress.md`](progress.md) and [`release-manifest.json`](release-manifest.json) first.

## What you can rely on

- All of M01–M14 **code** is on `main` (PRs #2–#15 merged). Registrations exist under `backend/modules/*/registration.py`.
- Contracts revision `school-contracts-v15` with M02–M14 frozen; common schemas frozen.
- Standalone profile + fakes work per module. M14 binds real `PlatformAdapter` in standalone.
- C02 packet forbids silent fakes in integrated mode and forbids regenerating modules.

## What you cannot claim

- Independent standalone approval for any of M01–M14.
- M01 contract freeze (still `not_started` in `contracts/manifest.json`).
- M02 as a complete registry / `RegistryPort` provider.
- Any suite result not recorded from an actual run on this branch.

## Real adapter map (target)

| Port | Owning module | Factory (existing code) | Status at inventory |
|---|---|---|---|
| `access` | M01 | `modules.access.services.authorize.AccessService` | Code exists; contracts unfrozen |
| `registry` | M02 | **missing** — must implement `RegistryPort` | **BLOCKER** |
| `timetable` | M03 | `modules.timetable.services.port.TimetableService` | Exists |
| `attendance` | M04 | `modules.attendance.services.port.AttendanceService` | Exists |
| `assessment` | M05 | `modules.assessment.services.port.AssessmentService` | Exists |
| `performance` | M06 | `modules.performance.services.port.PerformanceService` | Exists |
| `fees` | M07 | `modules.fees.services.port.FeesService` | Exists |
| `files` | M12 | `modules.files.services.port.FilesService` | Exists |
| `platform` | M14 | `modules.platform.services.adapter.PlatformAdapter` | Exists |
| `notifications` | M11 | communications NotificationPort adapter if present | Verify before bind |
| `object_storage` | shared/infra | production-shaped adapter | Verify; refuse if missing |
| `clock` | shared | real clock | Exists |

Integrated must **raise** when a declared consumer has no real provider.

## Assembly order

`M00 → M14 → M01 → M02 → M12 → M03 → M04 → M05 → M07 → M08 → M09 → M10 → M06 → M11 → M13`

## Migration notes

- Keep module migrations as shipped; do not rewrite deployed migration files.
- Document host order in `docs/integration/migration-order.md` once Django graph is confirmed on nonempty DB.
- Cross-module refs stay UUIDs (or documented stable registry/file FKs). No cascade delete of published results, ledgers, or evidence.

## M01 contract conflict (do not silent-freeze)

- **Provider:** M01 Access on `main`
- **Consumer:** every module consuming `access`
- **Approved schema:** none — revision.json explicitly leaves M01 unfrozen
- **Conflict:** artefacts hashed but `modules.M01.status == not_started`
- **Minimum correction:** human review of `contracts/M01/`; add `frozen_modules.M01` in `contracts/revision.json`; regenerate manifest
- See also: `docs/integration/m01-contract-conflict.md` (added with wiring)

## Open defects

1. M02 incomplete — blocks all registry-backed journeys.
2. Zero STANDALONE_VERIFIED.
3. `dev.py` lacks `all` / `integration` / `load` / `restore` until C02 host work lands.
4. Frontend OpenAPI client generation covers only M00/M01/M03 today.

## How a fresh chat continues

1. `git checkout c02/integration && git pull`
2. Read this file + `progress.md` + `release-manifest.json`
3. Resume the first unchecked item in `progress.md`
4. Never mark a gate passed without executing it
5. Push draft PR only; do not merge or deploy
