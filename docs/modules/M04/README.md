# M04 attendance

Status: **contract proposed — awaiting review**. No implementation yet.

- Progress: [`progress.md`](progress.md)
- Contract packet: [`contracts/M04/PACKET.md`](../../../contracts/M04/PACKET.md)
- Review decisions: [`contracts/M04/review-decisions.md`](../../../contracts/M04/review-decisions.md)
- Code will live in `backend/modules/attendance/` and `frontend/src/features/attendance/`
- Nothing here is importable yet: `backend/modules/attendance/` deliberately has no
  `__init__.py`.

## Before writing any code

Proposed OpenAPI, schemas, ports, errors and fixtures are in `contracts/M04/`.
They must be reviewed and frozen in `contracts/manifest.json` before
implementation.

## B00 note

Attendance is required for EVERY period of the central timetable. This granularity is fixed by B00 and is not a per-deployment decision.
