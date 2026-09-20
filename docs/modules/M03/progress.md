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

**Phase: all four implementation steps complete. STANDALONE_VERIFIED is false —
the container-backed suites have never been executed on this machine, and no
second developer has verified the module from a fresh checkout.**

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m03/timetable-calendar` |
| Branched from | `aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a` (`main`) |
| Manifest revision | `school-contracts-v4`, status `reviewed` |
| M03 manifest status | **`frozen`**, reviewed by Abhinav M on 2026-09-20; 27 frozen entries where 20 were before |
| PR | **Draft #4** — https://github.com/Aravind-Unni/School-Managment-Software/pull/4 |
| Recorded | 2026-09-20 |

## Complete

### Contract gate (commits `07a42ad`, `0350ce7`)

Proposed, reviewed and frozen: OpenAPI (21 operations over 16 paths), 35 closed
DTO definitions, both event payloads, 33 error rows and 7 conflict codes, the
provided and consumed port signatures, and a deterministic synthetic scenario
with 12 machine-validated response examples.

All fourteen review items were approved as proposed. The three that could not be
answered without the reviewer were each put with their alternatives:

- the packet's event names (`TimetablePublished.v1`) are rejected by the frozen
  envelope's lowercase two-segment pattern -> **conform** (`timetable.published`),
  rather than revise a shared schema every module and the outbox depend on;
- a substitution's authority lasts to the **end of its own school day**,
  Asia/Kolkata, exclusive; earlier is allowed, later is 422;
- **no working-day override**: a school day is a weekday the effective revision
  defines periods for, with no holiday in force, so the weekly pattern stays the
  school's own data and nothing here assumes which days a school teaches.

### Tests, written first (commit `25f8280`)

Written from the frozen contract with no implementation to read, and failing for
exactly one reason — `modules.timetable.registration` was absent. 17 passed at
that point: the contract-artefact assertions, which need no module.

### Backend (commit `26d8efa`)

All four steps. 146 tests pass on the SQLite profile.

- **Step 1** — period templates and the draft weekly editor. Half-open period
  overlap (abutting periods are an ordinary school day, not a clash), closed write
  bodies at every nesting depth, whole-week replace under `expected_version`, and
  a published grid that cannot be edited.
- **Step 2** — the pure conflict detector. Order-independent, monotonic and
  clock-free; rules are data in `CONFLICT_SPECS`. Three conflicts are unreachable
  through the API because the write boundary refuses them first, and are detected
  anyway so a revision stored before a rule existed is still caught.
- **Step 3** — publication and the calendar. Forward-only; publishing CLOSES the
  previous revision rather than deleting it. Version is checked before state, so
  two academic heads publishing one draft get a version conflict. Audit and outbox
  are appended in the writing transaction, and the rollback is asserted.
- **Step 4** — substitutions, single-period cancellation and the attendance port.
  Expiry is applied in exactly one place, the teaching authority; the schedule
  views keep showing a substitute afterwards, because they record who taught.

The stable dated identity is `uuid5(namespace,
"{school}:{section}:{date}:{slot_code}")`. It excludes the revision, the slot row
and the period's start time, so republishing a grid — or moving P2 from 09:30 to
09:45 — reuses every session id and creates no duplicate attendance identity.

### Frontend (commit `5ecd5f6`)

Four routes: the weekly editor with its conflicts list and publish preview,
date-specific substitution, a class schedule and a teacher's own schedule. Both
languages, today first on mobile, and every loading, empty, error and denied state
rendered from a message key. 63 frontend tests pass on Node 22.22.2, 16 of them
new. The typed client is generated from the frozen OpenAPI, never hand-written.

## Observed checks

Every number below was observed in this session. The profile is named for each,
because a SQLite result is not a PostgreSQL result.

| Command / check | Result |
|---|---|
| `dev.py doctor` | **exit 2** — no container engine (dangling Docker Desktop symlinks only) |
| `dev.py check M03 --suite contracts` | **PASS** — manifest current (27 frozen), 7 architecture checks, 105 shared + 24 M03 contract tests |
| `pytest tests/modules/M03` (MODULE_ID=M03, SQLite) | **146 passed** |
| `pytest` (foundation suite, M00 profile, SQLite) | **295 passed** |
| `ruff check .` / `ruff format --check .` | clean |
| `arch_check.py` | 7 checks passed |
| `makemigrations --check --dry-run` | no changes detected |
| `spectacular --fail-on-warn` | exit 0 |
| generated schema vs frozen OpenAPI | **identical** — same 21 operationIds, same 16 paths. A contract test asserts it |
| `npx vitest run` (Node 22.22.2) | **63 passed** (16 new) |
| `npm run lint` / `typecheck` / `build` | clean |
| `dev.py check M03 --suite standalone` | **NOT RUN** — no running stack. Recorded `not-run`, never as passing |
| `dev.py check M03 --suite browser` | **NOT RUN** — no running stack |
| `dev.py evidence M03` | bundle written; `all_suites_passed: false`, correctly |

`mypy` reports 76 errors under `modules/timetable`, of the same two kinds M01 and
M02 already report (`request.school_context` on DRF's `Request`, and duck-typed
`object` ports). It is not a CI gate and was already red repo-wide at 240 errors
before this branch; nothing here made it worse in kind.

## Incomplete

- **Nothing in the module's own scope.** Every operation the frozen contract
  declares is served, and every acceptance case in
  `contracts/M03/fixtures/expected-results.json` has a test.
- **The container path has never been executed** — by this session or by anyone.
- **The three PENDING integration cases** in the handoff stay pending.

## Changed interfaces

Files outside `backend/modules/timetable`, `frontend/src/features/timetable`,
`tests/modules/M03`, `dev/modules/M03` and `docs/modules/M03`. None was changed
silently; each is listed here and in the handoff.

| File | Change | Why |
|---|---|---|
| `contracts/manifest.json`, `contracts/revision.json` | M03 recorded and frozen | The review gate's outcome |
| `tests/integration/test_dev_cli.py` | M03 added to the implemented list | That list is derived from `registration.py`; M01 and M02 did the same |
| `frontend/src/shared/i18n/LanguageContext.tsx` | merges the timetable catalogue | Nav labels are rendered by the shell, so without it they render as keys. M01's catalogue is merged the same way |
| `frontend/playwright.config.ts` | `MODULE_ID` selects the spec | A one-module stack serves one module's routes. Generalised from the existing M01 special case rather than adding a third `if` |
| `scripts/dev.py` | passes `MODULE_ID` into the browser suite | Without it the runner collected every spec and drove them at routes the running stack does not serve |
| `frontend/package.json`, `frontend/src/app/registeredModules.ts`, `frontend/tests/unit/moduleRegistry.test.ts` | M03 registered | The module's own registration entry |

No file under `backend/contracts`, `backend/shared` or `contracts/common` was
touched, no guard was weakened, and no frozen hash was moved.

## Exact next step

**Run the container-backed suites on a machine with a container engine**, in this
order, and attach the evidence to the commit actually tested:

```bash
python3 scripts/dev.py up M03 --profile standalone
python3 scripts/dev.py migrate M03 --profile standalone
python3 scripts/dev.py seed M03 --scenario baseline
python3 scripts/dev.py check M03 --suite standalone
python3 scripts/dev.py check M03 --suite browser
python3 scripts/dev.py evidence M03
```

Then have a second developer verify the module from a fresh checkout. Only after
both is `STANDALONE_VERIFIED` true. The draft PR (#4) is open and must not be
merged before either happens.

## Blockers

1. **No container engine on this machine.** `dev.py doctor` exits 2. The
   standalone suite against real PostgreSQL and the Playwright browser suite
   cannot run here, and are recorded `not-run` — never as passing. Migrations
   applying to PostgreSQL, JSONB behaviour, row locking and the
   two-simultaneous-stacks requirement are all unverified for this module.
2. **B00's own acceptance gate is still open** — merged without peer review, four
   criteria unverified, the container path never executed by anyone. Inherited,
   and not closeable from here.
3. **Four Registry validations are impossible** with the frozen port: no
   `get_section`, `get_subject`, `get_staff` or `get_academic_year`. So a slot's
   subject is unvalidated, an unknown teacher is indistinguishable from an
   unassigned one, a version's range is never checked against its year, and the UI
   can offer no picker with names. Recorded in `contracts/M03/ports.md`, not
   worked around.
4. **A cancellation's version cannot be read back.** The frozen
   `PeriodSessionDTO` is closed and carries none, so a client that did not make
   the cancelling write cannot restore the period. A contract revision item, in
   the handoff.
