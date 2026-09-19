# M13 exchange

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M13/PACKET.md`](../../../contracts/M13/PACKET.md)
- Code will live in `backend/modules/exchange/` and `frontend/src/features/exchange/`
- Nothing here is importable yet: `backend/modules/exchange/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M13` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

_No module-specific note in the B00 packet beyond the inherited constraints above._
