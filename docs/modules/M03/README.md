# M03 timetable

Status: **implemented, contract frozen, not standalone-verified.**

- Where things stand: [progress.md](progress.md)
- How to pick this up cold: [handoff.md](handoff.md)
- What has and has not been observed: [acceptance.json](acceptance.json)
- Contract: [`contracts/M03/PACKET.md`](../../../contracts/M03/PACKET.md), frozen
  under `school-contracts-v4`
- **Read before changing anything here:**
  [`contracts/M03/review-decisions.md`](../../../contracts/M03/review-decisions.md)
  and [`ports.md`](../../../contracts/M03/ports.md) — the fourteen reviewed
  decisions, and the four validations this module cannot perform because the
  frozen Registry port does not expose them.

Code lives in `backend/modules/timetable/` and `frontend/src/features/timetable/`.

## The one thing to know

A dated period's identity is derived, not stored:

```
uuid5(namespace, "{school_id}:{section_id}:{date}:{slot_code}")
```

It deliberately excludes the timetable version, the slot row id and the period's
start time, because all three move when a school publishes a revision. Attendance
is written against that id, so if it moved, every past register would orphan.

## B00 note

Owns the central timetable. Attendance depends on its periods.
