# M14 platform

Status: **contract proposed — awaiting freeze**. No implementation code yet.

- Contract packet: [`contracts/M14/PACKET.md`](../../../contracts/M14/PACKET.md)
- Review decisions: [`contracts/M14/review-decisions.md`](../../../contracts/M14/review-decisions.md)
- Progress: [`progress.md`](progress.md)
- Code will live in `backend/modules/platform/` and `frontend/src/features/platform/`
- Nothing is importable yet until after freeze and step-1 implementation.

## Before writing any code

Review and freeze the proposed OpenAPI, JSON Schema, ports, error enums and
fixtures in `contracts/manifest.json`. Only then implement.
