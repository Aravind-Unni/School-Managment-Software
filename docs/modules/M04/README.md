# M04 attendance

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M04/PACKET.md`](../../../contracts/M04/PACKET.md)
- Code will live in `backend/modules/attendance/` and `frontend/src/features/attendance/`
- Nothing here is importable yet: `backend/modules/attendance/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M04` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Attendance is required for EVERY period of the central timetable. This granularity is fixed by B00 and is not a per-deployment decision.
