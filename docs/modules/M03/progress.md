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

**Phase: all four implementation steps complete, and BOTH container-backed suites
pass in CI against a real stack on commit `6d7e53e` (including the denial and
pupil journeys). STANDALONE_VERIFIED is still false, for one remaining reason:
no second developer has verified the module from a fresh checkout.**

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m03/timetable-calendar` |
| Branched from | `aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a` (`main`) |
| Manifest revision | `school-contracts-v4`, status `reviewed` |
| M03 manifest status | **`frozen`**, reviewed by Abhinav M on 2026-09-20; 27 frozen entries where 20 were before |
| PR | **Draft #4** — https://github.com/Aravind-Unni/School-Managment-Software/pull/4 |
| Head | `6d7e53e` |
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

Five routes: the weekly editor with its conflicts list and publish preview,
date-specific substitution, and read-only class, teacher and pupil schedules. Both
languages, today first on mobile, and every loading, empty, error and denied state
rendered from a message key. 65 frontend tests pass on Node 22.22.2, 18 of them
new. The typed client is generated from the frozen OpenAPI, never hand-written.

The pupil view shows a period teaching a subject the pupil is not enrolled in and
MARKS it: hiding it leaves an unexplained gap in the day, and showing it unmarked
tells a pupil to attend a lesson they are not in.

## Observed checks

Every number below was observed in this session. The profile is named for each,
because a SQLite result is not a PostgreSQL result.

| Command / check | Result |
|---|---|
| `dev.py doctor` | **exit 2** — no container engine (dangling Docker Desktop symlinks only) |
| `dev.py check M03 --suite contracts` | **PASS** — manifest current (27 frozen), 7 architecture checks, 105 shared + 24 M03 contract tests |
| `pytest tests/modules/M03` (MODULE_ID=M03, SQLite) | **148 passed** |
| `pytest` (foundation suite, M00 profile, SQLite) | **316 passed** |
| `ruff check .` / `ruff format --check .` | clean |
| `arch_check.py` | 7 checks passed |
| `makemigrations --check --dry-run` | no changes detected |
| `spectacular --fail-on-warn` | exit 0 |
| generated schema vs frozen OpenAPI | **identical** — same 21 operationIds, same 16 paths. A contract test asserts it |
| `npx vitest run` (Node 22.22.2) | **65 passed** (18 new) |
| `npm run lint` / `typecheck` / `build` | clean |
| `dev.py check M03 --suite standalone` (this machine) | **NOT RUN** — no container engine. Recorded `not-run`, never as passing |
| `dev.py check M03 --suite browser` (this machine) | **NOT RUN** — no container engine |
| `dev.py check M03 --suite standalone` (**CI**, commit `b5d91d7` and later) | **422 passed** against `postgres-container` |
| `dev.py check M03 --suite browser` (**CI**, commit `b5d91d7`) | **8 passed** — before the denial and pupil journeys were added |
| `m03-browser` (**CI**, commit `08d841a`) | **FAIL** — 7 passed, 2 failed. Cause below |
| `m03-browser` (**CI**, commit `6d7e53e`) | **PASS** — 9 Playwright tests against the real stack |
| `m03-backend` (CI) | migrations on an EMPTY then a POPULATED PostgreSQL 17.11, the suite, and the served surface matching the frozen OpenAPI |
| full CI on `6d7e53e` | **all jobs green** (run [35522082353](https://github.com/Aravind-Unni/School-Managment-Software/actions/runs/35522082353)) |
| `npx vitest run` / lint / typecheck (this session, Node 22.22.2) | **65 passed**, lint and typecheck clean |
| `dev.py check M03 --suite contracts` (this session) | **PASS** — manifest, arch, 105 shared + 24 M03 |

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
| `tests/conftest.py`, `tests/integration/test_standalone_isolation.py`, `tests/contracts/test_registration_contract.py` | the standalone suite works for every module | Defect 1 below. Two assertions widened to cover every module rather than the M00 placeholder |
| `backend/shared/http/context.py`, `backend/shared/http/middleware.py`, `backend/config/settings/standalone.py`, `dev/harness/compose.py` | the containerised stack can reach its own dev persona | Defect 2 below. **A shared runtime change; wants review on its own terms** |
| `tests/integration/test_dev_persona_peer.py` | new | The 21 assertions pinning that fix, including production's refusal and the port publication it depends on |
| `frontend/tests/unit/timetable.test.tsx`, `frontend/tests/browser/timetable.spec.ts` | new | M03's own frontend tests. They live in the shared test directories because that is where the runner and Playwright collect from |
| `.github/workflows/ci.yml` | two M03 jobs added | `m03-backend` runs the suite and both migration paths against real PostgreSQL; `m03-browser` brings the stack up and runs the standalone AND browser suites. Copied from the `m01-backend`/`m01-browser` pattern. This is the only place those two suites CAN run, since no machine here has a container engine |

No file under `backend/contracts`, `backend/shared` or `contracts/common` was
touched, no guard was weakened, and no frozen hash was moved.

## Exact next step

**A second developer verifies the module from a fresh checkout.** Only then is
`STANDALONE_VERIFIED` true. The draft PR (#4) is open and must not be merged
before that happens. CI on `6d7e53e` is fully green, including `m03-browser`.

## What this session fixed (CI red on `m03-browser`)

After the denial and pupil journeys were added (`f5b3972`, `d672da3`), CI on
`08d841a` failed two Playwright tests with **strict-mode locator violations**,
not product regressions:

- `getByLabel("Class")` matched both the select labelled "Class" and the
  `<section>` whose heading is "Class schedule" (Playwright label match is a
  substring by default).
- `getByLabel("Pupil")` likewise matched the "Pupil" field and "Pupil schedule".

Fixed by targeting the controls by role (`combobox` / `textbox`) so they cannot
collide with the page region. Also kept a small UI fix already in the working
tree: the class and substitution pages no longer write the resolved default
section back into state on first load (that re-ran the effect and double-fetched).
Observed green on `6d7e53e` (run 35522082353).

## What running the container path for the first time exposed

Two defects, both latent since B00 and both invisible until now, because no
module's standalone or browser suite had ever been executed against a real stack.
M01's CI job runs only its browser suite, and no machine in this session has a
container engine.

1. **`dev.py check <ID> --suite standalone` was broken for every module but M00.**
   It runs the whole `tests/` tree under the target profile, which installs one
   business app — so three shared tests written against the M00 placeholder
   failed at COLLECTION and took the entire run with them. Fixed in `1667571`:
   the two demo-specific integration files are collected under M00 only, and the
   isolation and registration assertions now read `MODULE_ID` instead of
   hardcoding the demo. Two assertions got WIDER, not weaker — they now verify
   the isolation property for whichever module is under test.
2. **The containerised stack could not reach its own development persona.** Every
   browser request came back 401. The persona requires a loopback peer; the stack
   publishes the API to `127.0.0.1` only, but Docker NATs the connection, so the
   peer the container sees is the bridge gateway. Fixed in `b5d91d7` by letting a
   profile declare trusted peer NETWORKS — empty by default, the private ranges
   in the generated Compose file, and refused outright in production, which is
   pinned by 21 new tests including "production refuses even with `0.0.0.0/0`
   declared" and "the generated stack still publishes to 127.0.0.1, never
   0.0.0.0".

Both are **shared runtime changes** and want review on their own terms. They are
on this branch because no module's browser suite can pass without them.

## Blockers

1. **No second developer has verified the module from a fresh checkout.** This is
   the one remaining condition for `STANDALONE_VERIFIED`.
2. **Nothing about the container path can be verified on this machine.**
   `dev.py doctor` exits 2. Every container result quoted above is CI's, attached
   to the commit CI actually tested.
3. **B00's own acceptance gate is still open** — merged without peer review, four
   criteria unverified, the container path never executed by anyone. Inherited,
   and not closeable from here.
4. **Four Registry validations are impossible** with the frozen port: no
   `get_section`, `get_subject`, `get_staff` or `get_academic_year`. So a slot's
   subject is unvalidated, an unknown teacher is indistinguishable from an
   unassigned one, a version's range is never checked against its year, and the UI
   can offer no picker with names. Recorded in `contracts/M03/ports.md`, not
   worked around.
5. **A cancellation's version cannot be read back.** The frozen
   `PeriodSessionDTO` is closed and carries none, so a client that did not make
   the cancelling write cannot restore the period. A contract revision item, in
   the handoff.
