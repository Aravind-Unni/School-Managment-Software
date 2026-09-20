# M03 handoff

## Read first

The contract gate is **closed**: the packet was approved as proposed and frozen
under revision `school-contracts-v4` on 2026-09-20 by Abhinav M. **All four
implementation steps are complete and passing on the SQLite profile.**

`STANDALONE_VERIFIED` is **false**, and nothing in this session could make it
true. This machine has no container engine, so the standalone suite against real
PostgreSQL and the Playwright browser suite recorded `not-run`, and no second
developer has verified the module from a fresh checkout.

Read [progress.md](progress.md) first — it lists every check actually run, with
the profile each ran on. Then the [packet](../../../contracts/M03/PACKET.md),
[review decisions](../../../contracts/M03/review-decisions.md) and
[ports.md](../../../contracts/M03/ports.md).

Do not mistake the SQLite test profile for standalone verification.

Session source: branch `m03/timetable-calendar`, branched from `main`
`aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a`, revision `school-contracts-v4`.

## What is available

The whole module. 21 operations over 16 paths under `/api/v1`, and the generated
schema matches the frozen `contracts/M03/openapi.json` operation for operation —
a contract test asserts exactly that.

Serving today:

| Path | What it does |
|---|---|
| `timetables` | list revisions; create a draft |
| `timetables/{id}` | read one revision with its grid; replace a DRAFT's grid |
| `timetables/{id}/validate` | the conflicts list, read-only |
| `timetables/{id}/publish` | publish under `expected_version`, with step-up |
| `timetables/current` | one section's effective schedule for a date |
| `teacher-schedule`, `student-schedule` | a teacher's day, a pupil's day |
| `calendar`, `calendar-exceptions` | the school calendar and its exceptions |
| `teacher-unavailability` | recorded staff unavailability |
| `substitutions` | assign and withdraw dated cover |
| `sessions/{id}`, `sessions/{id}/cancellation` | one dated period; cancel or restore it |

Seven tables with migrations and no drift. React routes at `/timetable/editor`,
`/timetable/substitutions`, `/timetable/class` and `/timetable/teacher`, in
English and Malayalam.

In-process, for M04: `modules.timetable.api.deps.timetable_port()` returns
`get_sessions`, `get_session`, `get_calendar` and `get_teaching_authority`.

## Startup commands

Use the `up` output for real URLs; ports are allocated dynamically and are never
fixed. **None of the container-backed commands has been run for M03**, because
this machine has no container engine.

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M03 --profile standalone
python3 scripts/dev.py migrate M03 --profile standalone
python3 scripts/dev.py seed M03 --scenario baseline
python3 scripts/dev.py check M03 --suite standalone
python3 scripts/dev.py check M03 --suite contracts
python3 scripts/dev.py check M03 --suite browser
python3 scripts/dev.py evidence M03
python3 scripts/dev.py down M03
```

## Printed URLs

None recorded — no stack was started. `dev.py up` prints the allocated API and
frontend URLs. Do not assume a port.

## Fictional login instructions

There is no login. The standalone profile derives a **fixed synthetic persona
server-side**, on loopback only: **T1, the class teacher of C1**
(`eda913d7-a893-5ecc-af4e-766d1332b2ee`). The browser cannot select or change it,
and any client-asserted identity header is answered with a hard 400.

As T1 you can read C1's schedule, build and publish a draft, and assign cover. To
see a denial, ask for C2 — T1 has no assignment to it, and the answer is 403 in
prose. Real login, sessions and 2FA are M01's and stay **explicitly pending**.

## Manual actions and expected outcomes

| Action | Expected |
|---|---|
| Open `/timetable/class`, date 2026-07-15 | two periods, P1 and P2 |
| Same page, date 2026-07-16 | "No lessons on this day — Holiday", no periods |
| Same page, date 2026-07-22 | two periods; an exam day is still a teaching day |
| Switch language to മലയാളം | every label and message translates; no key renders as itself |
| Open `/timetable/editor`, press "Check for conflicts" | advisory `teacher_not_assigned` rows for the seeded grid, nothing blocking |
| Build a draft placing T1 in C1 P1 and C2 P1 | validate reports `teacher_double_booked`; publish is refused, 409 |
| Publish a clean draft | 200, the previous revision is closed, not deleted, and stays readable |
| Assign a substitute on `/timetable/substitutions` | 201; the screen states the access ends with that school day |

## Migrations

One: `backend/modules/timetable/migrations/0001_initial.py`, creating seven
tables. `makemigrations --check --dry-run` reports no drift. **No irreversible
migration**: it is a pure create, reversible by dropping the tables, and no data
is transformed. It has been applied to a fresh SQLite database only; applying it
to PostgreSQL, empty and seeded, is outstanding.

## Commands actually run this session, and their results

| Command | Result |
|---|---|
| `dev.py doctor` | exit 2 — no container engine; Node on PATH is v20.19.5 |
| `dev.py check M00 --suite contracts` (session start) | passed — the foundation was green before any change |
| `dev.py check M03 --suite contracts` | **passed** — 27 frozen entries, 7 architecture checks, 105 shared + 24 M03 contract tests |
| `pytest tests/modules/M03` (SQLite) | **147 passed** |
| `pytest` (foundation, SQLite) | **295 passed** |
| `ruff check` / `ruff format --check` / `arch_check.py` | clean |
| `makemigrations --check --dry-run` | no changes |
| `spectacular --fail-on-warn` | exit 0; output matches the frozen OpenAPI exactly |
| `npx vitest run` on Node 22.22.2 | **63 passed** |
| `npm run lint` / `typecheck` / `build` | clean |
| `dev.py check M03 --suite standalone` | **not-run**: no running stack |
| `dev.py check M03 --suite browser` | **not-run**: no running stack |
| `dev.py evidence M03` | `all_suites_passed: false` |

Node on PATH is v20.19.5, on which `vitest` cannot start a worker at all
(`webidl.util.markAsUncloneable is not a function`, from jsdom's undici). The
suite was run on the nvm-installed **22.22.2**, the exact version CI pins.

## CI

Two jobs were added on this branch, following the `m01-backend` / `m01-browser`
pattern, because CI is the only place the container-backed suites can run:

* **`m03-backend`** — migrations applied to an EMPTY database, then the seed, then
  migrations re-applied to a POPULATED one, then the M03 suite against real
  PostgreSQL 17.11, then a check that the served surface still matches the frozen
  OpenAPI.
* **`m03-browser`** — brings the real stack up with `dev.py up M03`, migrates,
  seeds, and runs **both** the standalone and the browser suites against the
  allocated URLs, uploading the evidence bundle.

Their result on PR #4 is the only evidence that the container path works. Do not
assume it from this document.

## Contract revision items found by implementing

Real disagreements between frozen artefacts and what building against them needs.
None was resolved by editing a frozen file.

1. **A cancellation's version cannot be read back.** `SessionCancellationRequest`
   requires `expected_version`, described as "the cancellation record's version",
   but `PeriodSessionDTO` is a closed shape with no version field and there is no
   other endpoint that exposes one. A client tracks it from its own writes — the
   first cancel leaves it at 1 — but a client that did not make those writes
   cannot restore the period at all. Needs either a version on the response or a
   cancellation read endpoint.
2. **No error key for a duplicate calendar exception.** The frozen rows have no
   `timetable.error.calendar_exception_exists`, so a second live exception for the
   same date and kind is refused as a generic 422 with a field error on `date`.
   The next revision should name it.
3. **Trailing slashes.** `openapi.json` declares every path without one
   (`/timetables`); the shared `API_PATH_ROOT_PATTERN` requires every declared
   ROOT to end in one (`timetables/`). `registration.py` declares the slashed
   form and `urls.py` serves the bare one — the same split M02 recorded, carried
   here so the two modules do not diverge. Serving both forms produces duplicate
   operationIds and fails `spectacular --fail-on-warn`.
4. **Four Registry lookups do not exist**: `get_section`, `get_subject`,
   `get_staff`, `get_academic_year`. Consequences, none worked around: a slot's
   subject is never validated; an unknown teacher id is indistinguishable from an
   unassigned teacher, which is why `teacher_not_assigned` is advisory; a
   revision's effective range is never checked against the year it names; and the
   UI can offer no picker with names, so it shows shortened ids. Proposed
   signatures are in `contracts/M03/ports.md`.
5. **`TimetablePort` is not in `backend/contracts/ports.py`.** Adding it is an
   additive shared revision (review item 2) and was deferred, as approved. The
   concrete service is at `modules.timetable.services.port.TimetableService` and
   is reachable through `api/deps.timetable_port()`.
6. **Reverse session lookup is a bounded search.** A `uuid5` identity cannot be
   reversed, so `GET /sessions/{id}` finds a substituted or cancelled period
   directly (those rows store the identity) and otherwise recomputes identities
   over the published revisions' own date ranges, capped at 400 days each. Correct
   and small for one school; a materialised session index is the obvious
   optimisation.

## Pending integration tests

**PENDING, not passing.** Independent approval of M03 does not imply any of them.
Replace the fakes and run them in Section C.

1. **Real attendance authorisation for a dated substitution.** M03 proves it
   publishes the trusted fact and that the fact expires — `get_teaching_authority`
   reports the substitute only while `valid_until` has not passed. It cannot prove
   M04 honours it; M04 does not exist.
2. **Real authentication and 2FA.** Step-up on publish is exercised against the
   fake Access adapter only, at the service boundary with an aged context.
3. **Real Registry provider.** The four lookups above do not exist, so four
   validations are not performed against anything.

Also unprovable against the fake, and recorded rather than claimed: the shared
`FakeAccess` has no per-actor grants, so every persona holds every school-scoped
action. A denial that depends on WHO the actor is — a teacher who may not publish,
a colleague reading another teacher's day — cannot be demonstrated here. What is
demonstrated is which action the module ASKS about, asserted by recording the
calls it makes to Access.

## Blockers for whoever picks this up

1. No container engine here → the standalone and browser suites cannot run, and
   nothing about PostgreSQL behaviour is verified for this module.
2. B00's acceptance gate is still open, and is not closeable from this module.
3. The six contract revision items above.

The branch is pushed and draft PR
[#4](https://github.com/Aravind-Unni/School-Managment-Software/pull/4) is open.
It is a draft on purpose: two of the three suites have never run.
