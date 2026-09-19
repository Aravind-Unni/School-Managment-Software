# M14 platform

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M14/PACKET.md`](../../../contracts/M14/PACKET.md)
- Code will live in `backend/modules/platform/` and `frontend/src/features/platform/`
- Nothing here is importable yet: `backend/modules/platform/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M14` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Owns the REAL audit/outbox and production deployment. Uses its ACTUAL implementation, not the harness test adapter. Production deployment is covered here; Kubernetes is NOT required.
