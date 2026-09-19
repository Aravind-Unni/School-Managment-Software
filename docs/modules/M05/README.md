# M05 assessment

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M05/PACKET.md`](../../../contracts/M05/PACKET.md)
- Code will live in `backend/modules/assessment/` and `frontend/src/features/assessment/`
- Nothing here is importable yet: `backend/modules/assessment/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M05` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Teachers grade written work. Students and authorised guardians see their own answer sheets only AFTER grading and result publication.
