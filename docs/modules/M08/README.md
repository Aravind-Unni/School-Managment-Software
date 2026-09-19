# M08 transport

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M08/PACKET.md`](../../../contracts/M08/PACKET.md)
- Code will live in `backend/modules/transport/` and `frontend/src/features/transport/`
- Nothing here is importable yet: `backend/modules/transport/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M08` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

No GPS is in scope.
