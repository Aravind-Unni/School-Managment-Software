# M03 progress — central timetable and calendar

## Original request

Build M03 independently in four steps: (1) periods and the draft editor,
(2) conflict checks, (3) publication and calendar, (4) substitution and the
attendance port. Real Django/DRF, React/TypeScript, PostgreSQL and migrations;
deterministic fakes for external modules. One effective school timetable, teacher
and student views, calendar exceptions and substitutions; stable dated
`timetable_session_id` values for attendance; English/Malayalam UI; evidence and a
draft PR. Do not integrate other business modules, do not invent school policy, do
not merge or deploy. Propose contracts for review first.

## Current phase / source identity

**Phase: contract frozen. Tests next, then implementation steps 1-4. No module
code exists yet. STANDALONE_VERIFIED is false.**

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m03/timetable-calendar` |
| Branched from | `aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a` (`main`) |
| Manifest revision | `school-contracts-v4`, status `reviewed` |
| M03 manifest status | **`frozen`**, reviewed by Abhinav M on 2026-09-20; 27 frozen entries where 20 were before |
| PR | not opened yet |
| Recorded | 2026-09-20 |

## Complete

### Repository inspection

Read `AGENTS.md`, `docs/foundation/progress.md`, `contracts/manifest.json`,
`contracts/revision.json`, `contracts/common/*`, `contracts/M03/PACKET.md`, the
frozen `backend/contracts` DTOs and Protocols, `backend/shared` (fakes, port
binding, scope resolver, HTTP plumbing), the M01 and M02 implementations as the
house pattern, `scripts/dev.py`, `scripts/arch_check.py`,
`scripts/contract_manifest.py`, `tests/conftest.py` and the frontend shell.

The foundation was green at session start: `dev.py check M00 --suite contracts`
passed — manifest current, 7 architecture checks, 105 shared contract tests.

### Contract proposal (commit `07a42ad`)

Everything the packet requires before coding, in `contracts/M03/`:

- `openapi.json` — OpenAPI 3.1, 21 operations over 16 paths, every operation
  carrying its permission, its step-up requirement and the full error surface.
- `schemas/dtos.schema.json` — 35 closed definitions.
- `schemas/events.schema.json` — both event payloads.
- `error-codes.json` — 33 error rows and 7 conflict codes, all reusing the frozen
  `ErrorCode` enum. No enum member is added.
- `ports.md` — the provided `TimetablePort`, the four consumed ports, the stable
  dated session identity, and four gaps in the frozen `RegistryPort`.
- `fixtures/` — the deterministic synthetic baseline, 12 response examples and 2
  events (all machine-validated against the schemas), and 22 proposed acceptance
  cases marked clearly as *not* evidence.
- `review-decisions.md` — fourteen decisions requested, each with who is affected.

The manifest was first regenerated with the new files **hashed but not frozen**,
so drift was detectable while the gate was still open.

### Contract gate closed

All fourteen review items were **approved as proposed, with no revisions**, by
Abhinav M on 2026-09-20. The three that could not be answered without the reviewer
were each put with their alternatives:

- the packet's event names are rejected by the frozen envelope pattern -> conform to
  the envelope (`timetable.published`), do not revise a shared schema;
- a substitution's authority lasts to the **end of its own school day**, Asia/Kolkata,
  exclusive; earlier is allowed, later is 422;
- **no working-day override**: a school day is a weekday the effective version
  defines periods for, with no holiday in force.

Recorded in `contracts/M03/review-decisions.md` and in `contracts/revision.json`,
then frozen: `contracts/manifest.json` now holds 27 frozen entries where it held 20.

## Incomplete

Everything else. No backend app, no migrations, no API, no frontend, no tests, no
seed data. In order:

1. Periods and the draft editor
2. Conflict checks
3. Publication and calendar
4. Substitution and the attendance port

## Changed interfaces

None. No file under `backend/`, `frontend/`, `scripts/`, `contracts/common` or
`backend/shared` was modified. `contracts/manifest.json` and
`contracts/revision.json` changed only to record the new hashes and the review
outcome.

## Exact next step

Write `tests/modules/M03/` from the frozen contract, without reading an
implementation -- there is none -- and confirm every test fails for the right reason
before any code exists.

## Blockers

1. **No container engine on this machine.** `dev.py doctor` exits 2. The standalone
   suite against real PostgreSQL and the Playwright browser suite cannot run here;
   they will be recorded `not-run`, never as passing.
2. **Node v20.19.5 here, `frontend/package.json` requires `^22.22.2 || >=24`.** The
   frontend typecheck, unit tests and production build cannot run on this machine.
3. **B00's own acceptance gate is still open** — merged without peer review, four
   criteria unverified, the container path never executed by anyone. Inherited, and
   not closeable from here.
4. **Four Registry validations are impossible** with the frozen port: section,
   subject, staff and academic year lookups do not exist. Recorded in `ports.md`,
   not worked around.
