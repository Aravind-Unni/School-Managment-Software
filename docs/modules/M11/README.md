# M11 communications

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M11/PACKET.md`](../../../contracts/M11/PACKET.md)
- Code will live in `backend/modules/communications/` and `frontend/src/features/communications/`
- Nothing here is importable yet: `backend/modules/communications/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M11` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Local and test profiles must NEVER contact a real SMS or email provider.
