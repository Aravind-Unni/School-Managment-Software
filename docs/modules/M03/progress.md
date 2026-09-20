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

**Phase: contract proposal complete, awaiting the review gate. No module code
exists. STANDALONE_VERIFIED is false.**

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m03/timetable-calendar` |
| Branched from | `aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a` (`main`) |
| Manifest revision | `school-contracts-v4`, status `reviewed` |
| M03 manifest status | `not_started`; 7 artefacts hashed, **0 frozen** |
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

### Contract proposal (this commit)

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

The manifest was regenerated so the new files are **hashed but not frozen**: drift
on them is now detected, and M03's status stays `not_started`. The frozen-entry
count is unchanged at 20.

## Incomplete

Everything else. No backend app, no migrations, no API, no frontend, no tests, no
seed data. In order, after the gate closes:

1. Periods and the draft editor
2. Conflict checks
3. Publication and calendar
4. Substitution and the attendance port

## Changed interfaces

None. No file under `backend/`, `frontend/`, `scripts/`, `contracts/common` or
`backend/shared` was modified. `contracts/manifest.json` changed only by recording
the new unfrozen hashes.

## Exact next step

**Close the review gate.** A reviewer answers the fourteen items in
`contracts/M03/review-decisions.md`, then:

```bash
# after approval, and only then:
#  1. add M03 to contracts/revision.json under frozen_modules, with reviewer + date
#  2. python3 scripts/contract_manifest.py --update
#  3. commit as the freeze
```

Then write M03's tests from the frozen contract, without reading an implementation,
and confirm they fail for the right reason before any code exists.

## Blockers

1. **The review gate itself.** Fourteen open decisions; items 1 (event naming
   against the frozen envelope), 7 (how long a substitution lasts) and 9 (what makes
   a date a school day) cannot be answered by this module without guessing.
2. **No container engine on this machine.** `dev.py doctor` exits 2. The standalone
   suite against real PostgreSQL and the Playwright browser suite cannot run here;
   they will be recorded `not-run`, never as passing.
3. **Node v20.19.5 here, `frontend/package.json` requires `^22.22.2 || >=24`.** The
   frontend typecheck, unit tests and production build cannot run on this machine.
4. **B00's own acceptance gate is still open** — merged without peer review, four
   criteria unverified, the container path never executed by anyone. Inherited, and
   not closeable from here.
5. **Four Registry validations are impossible** with the frozen port: section,
   subject, staff and academic year lookups do not exist. Recorded in `ports.md`,
   not worked around.
