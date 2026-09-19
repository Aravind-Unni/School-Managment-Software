# M06 performance

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M06/PACKET.md`](../../../contracts/M06/PACKET.md)
- Code will live in `backend/modules/performance/` and `frontend/src/features/performance/`
- Nothing here is importable yet: `backend/modules/performance/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M06` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Reads from assessment and attendance. Forecasting history stores pooled aggregates only.
