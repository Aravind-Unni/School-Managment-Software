# M02 registry

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M02/PACKET.md`](../../../contracts/M02/PACKET.md)
- Code will live in `backend/modules/registry/` and `frontend/src/features/registry/`
- Nothing here is importable yet: `backend/modules/registry/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M02` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Owns people, sections and relationships. Provides RelationshipFacts; must never call Access from within relationship resolution.
