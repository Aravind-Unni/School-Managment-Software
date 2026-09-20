# M05 assessment

Status: **proposed — awaiting review**. Foundation (B00) is built; implementation
must not start until freeze.

- Contract packet: [`contracts/M05/PACKET.md`](../../../contracts/M05/PACKET.md)
- Review decisions: [`contracts/M05/review-decisions.md`](../../../contracts/M05/review-decisions.md)
- Progress: [`progress.md`](progress.md)
- Code will live in `backend/modules/assessment/` and `frontend/src/features/assessment/`
- Nothing is importable yet: `backend/modules/assessment/` has no `__init__.py`.

## Before writing any code

Review and freeze the proposed OpenAPI, JSON Schema, Protocol signatures, error
enums and fixtures in `contracts/manifest.json`. Only then implement.

## B00 note

Teachers grade written work. Students and authorised guardians see their own answer sheets only AFTER grading and result publication.
