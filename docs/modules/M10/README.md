# M10 alumni

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M10/PACKET.md`](../../../contracts/M10/PACKET.md)
- Code will live in `backend/modules/alumni/` and `frontend/src/features/alumni/`
- Nothing here is importable yet: `backend/modules/alumni/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M10` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

_No module-specific note in the B00 packet beyond the inherited constraints above._
