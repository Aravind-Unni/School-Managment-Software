# M03 timetable

Status: **contract proposed, awaiting review. No module code exists.**

- Contract proposal: [`contracts/M03/PACKET.md`](../../../contracts/M03/PACKET.md)
- **Read first:** [`contracts/M03/review-decisions.md`](../../../contracts/M03/review-decisions.md)
  — fourteen decisions a reviewer must make, and four validations this module
  cannot perform because the frozen Registry port does not expose them.
- Where things stand: [`progress.md`](progress.md)
- How to pick this up cold: [`handoff.md`](handoff.md)
- What has and has not been observed: [`acceptance.json`](acceptance.json)

Code will live in `backend/modules/timetable/` and
`frontend/src/features/timetable/`. Nothing there is importable yet:
`backend/modules/timetable/` deliberately has no `registration.py`, so no other
module can accidentally depend on it, `scripts/dev.py up M03` fails honestly rather
than serving an empty app, and `arch_check.py` rejects any import of it.

## Before writing any code

The manifest records M03 as `not_started`. Its artefacts are hashed — so drift is
detected — but **none is frozen**. Freezing is a human decision recorded in
`contracts/revision.json`, and it comes before tests, which come before code.

## B00 note

Owns the central timetable. Attendance depends on its periods.
