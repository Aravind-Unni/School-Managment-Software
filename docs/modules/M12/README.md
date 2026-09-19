# M12 files

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M12/PACKET.md`](../../../contracts/M12/PACKET.md)
- Code will live in `backend/modules/files/` and `frontend/src/features/files/`
- Nothing here is importable yet: `backend/modules/files/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M12` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Owns private S3-compatible storage. Access checks apply to private files, not only to API routes.
