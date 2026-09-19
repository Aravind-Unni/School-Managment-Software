# M03 timetable

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M03/PACKET.md`](../../../contracts/M03/PACKET.md)
- Code will live in `backend/modules/timetable/` and `frontend/src/features/timetable/`
- Nothing here is importable yet: `backend/modules/timetable/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M03` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Owns the central timetable. Attendance depends on its periods.
