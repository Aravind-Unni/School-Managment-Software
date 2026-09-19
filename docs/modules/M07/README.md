# M07 fees

Status: **not started**. The foundation (B00) is built; this module is not.

- Contract packet: [`contracts/M07/PACKET.md`](../../../contracts/M07/PACKET.md)
- Code will live in `backend/modules/fees/` and `frontend/src/features/fees/`
- Nothing here is importable yet: `backend/modules/fees/` deliberately has no
  `__init__.py`, so no other module can accidentally depend on it and
  `scripts/dev.py up M07` fails honestly rather than serving an empty app.

## Before writing any code

Produce the exact OpenAPI, JSON Schema, Protocol signatures, error enums and
example fixtures listed in the packet, get them reviewed, and freeze them in
`contracts/manifest.json`. Only then implement.

## B00 note

Money is integer INR paise. No full accounting and no payroll are in scope.
