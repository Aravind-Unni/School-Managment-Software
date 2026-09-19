# M01 access

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M01/PACKET.md`](../../../contracts/M01/PACKET.md)
- Code will live in `backend/modules/access/` and `frontend/src/features/access/`
- Nothing here is importable yet: `backend/modules/access/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M01` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Uses REAL login, sessions, TOTP and recovery, with a fake Registry ONLY. This is the one module that does not bind fake Access, because it IS Access.
