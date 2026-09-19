# M02 progress — Academic registry and student lifecycle

## Original request

Build M02 independently in four steps: (1) configuration and people,
(2) links and assignments, (3) enrolment lifecycle, (4) imports and historical
roster tests. Real Django/DRF, React/TypeScript, PostgreSQL and migrations;
deterministic external dependencies. Include English/Malayalam UI, effective
subject choices for every timetable period, guardian/teacher/self access,
duplicate review, transfers, promotion retry protection, withdrawal history,
validated exchange, evidence and draft PR. Do not invent school policy, integrate
other business modules, merge or deploy. Propose contracts for review first.

## Current phase / source identity

**Phase: implementation, step 1 of 4 complete. STANDALONE_VERIFIED is false.**
The contract gate is closed. Steps 2, 3 and 4 have not begun, and no frontend
code exists yet.

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m02/registry-contracts` |
| Head commit | `faeb9a2555a8639c33240ebf94da4d8c5a893345` |
| Starting main | `1d17113ea333b1c77743b6cfdfe3b3d2314089f1` |
| Commits ahead of main | 4 |
| Manifest revision | `school-contracts-v4` (was `school-contracts-v3-draft`) |
| M02 manifest status | `frozen`, reviewed by Abhinav M on 2026-09-20 |
| PR | **Unknown — could not be checked.** See "Blockers" below. |
| Recorded | 2026-09-20 |

## Complete

### Contract gate (commit `49e7512`)

The packet was approved as proposed, with no revisions. Recorded in
`contracts/M02/review-decisions.md` with reviewer and date, and in
`contracts/revision.json`, which is now the data the manifest generator reads.

Freezing it exposed that the generator could not express the decision. It
hardcoded both the revision string and "frozen means M00", and it globbed only
the top level of a module directory — so five contract files had never been
hashed at any point:

- `contracts/M02/schemas/dtos.schema.json` (3,549 lines)
- `contracts/M02/schemas/events.schema.json`
- `contracts/M01/schemas/dtos.schema.json`
- `contracts/M01/error-codes.json`
- `contracts/M01/openapi-seed.yaml`

The guard was reporting success over files it could not see. Discovery is now
recursive, revision and freeze state are data, and 20 entries are frozen where
13 were before.

### Step 1: configuration and people (commits `640762f`, `faeb9a2`)

Tests first, from the frozen contract, without reading an implementation —
because there was none. All 35 failed for the right reason before any code
existed. Four more were added to the contract suite afterwards.

- Eleven tables with migrations, no drift (`makemigrations --check` clean).
- School configuration installed by bootstrap; PUT updates under
  `expected_version` and never implicitly creates.
- Academic years, terms, standards, sections, subjects, with date-range,
  1–12 and per-school uniqueness rules. Archive preserves; no DELETE API.
- Students, guardians, staff, external identities.
- Cursor pagination with `items`/`next_cursor`; an invalid cursor or an
  out-of-range page size is refused, never silently clamped.
- Closed write shapes at every nesting depth: `school_id`, `version` and any
  unknown field are 422.
- The duplicate-review gate, described under "Decisions" below.

## Observed checks

Every number below was observed in this session on the **SQLite test profile**.

| Command/check | Result |
|---|---|
| `dev.py doctor` | Exit 2: no container engine (unchanged) |
| `dev.py check M02 --suite contracts` | **PASS**: 105 shared + 12 M02 contract tests, 7 architecture checks, manifest current |
| `pytest tests/modules/M02` | **PASS**: 39 tests |
| `pytest` (foundation default) | **PASS**: 295 tests |
| `pytest tests/modules/M01` | **PASS**: 53 passed, 1 skipped (needs PostgreSQL) |
| `makemigrations --check --dry-run` | **PASS**: no changes detected |
| `spectacular --fail-on-warn` (M02) | **PASS**: 0 errors, 0 warnings |
| `spectacular` (M00) diff vs frozen | **PASS**: byte-identical |
| `ruff check` / `ruff format --check` | **PASS** |
| `dev.py check M02 --suite standalone` | **not-run**: no PostgreSQL, no container engine |
| `dev.py check M02 --suite browser` | **not-run**: no running stack |
| `dev.py evidence M02` | FAIL: bundle incomplete; standalone and browser not-run |

`mypy` reports 61 errors in M02, the same django-stubs patterns already present
across M00 and M01 (which report 99). CI does not run mypy. Not treated as a
gate; recorded so nobody discovers it as a surprise.

## Decisions taken during implementation

1. **Duplicate detection is pure and rechecked under lock.** The rules live in
   `services/duplicates.py` with no IO. Everything they decide is rechecked
   inside the admission transaction, because a check outside it lets a candidate
   move between the reviewer's decision and the insert. An exact admission
   collision is never overridable; an exact name plus a non-null equal birth date
   raises a candidate a human judges; a null birth date matches nothing,
   including another null.
2. **A module-local fixture policy, not a test bypass.** The fake Access denies
   by default and the host factory passed no module rules, so every M02 endpoint
   would have 403'd in standalone. `shared/ports/bindings.py` now loads a
   module's own `fixture_policy.py`, with each action enumerated and no
   wildcard. This was the shared change approved in review-decisions.md.
3. **Unslashed paths, as the frozen OpenAPI declares them.** Serving both forms
   was tried and rejected: duplicate operationIds failed
   `spectacular --fail-on-warn`. See the contract-revision item in `handoff.md`.
4. **Four foundation state tests were updated**, and one was strengthened. See
   "Test changes" below — this is the item most deserving of a reviewer's eye.

## Test changes, stated plainly

`AGENTS.md` forbids modifying a test to make it pass. Five tests were changed.
Each is listed so the judgement can be checked rather than taken on trust.

**Three of my own step-1 tests, before they had ever passed:**

- Two asserted `response.json()["error"]["code"]`. Both frozen envelope schemas
  are flat and have no nested `error` object. The tests contradicted the
  contract; the contract is the authority.
- Two did not isolate the behaviour they named: the admission-number
  case-sensitivity test and the stale-token test each also tripped a different
  rule, so they would have passed for the wrong reason. Both were tightened, and
  the reason is written into the test docstring.

**Four foundation tests that encoded B00-era project state:**

`test_the_manifest_is_current...` asserted the literal revision string;
`test_no_business_module_contract_is_frozen_yet` asserted nothing was frozen;
`test_every_business_module_has_a_contract_packet` required "NOT STARTED" in
every packet; `test_implemented_modules_are_exactly_those_with_a_registration`
asserted `["M00", "M01"]`. All four become false the moment any module lands —
M01's own merge (`2556a07`) moved the last one the same way.

The freeze assertion was made **stronger**, not relaxed. It is now
`test_nothing_is_frozen_without_a_recorded_human_review`: a frozen module must
name the reviewer and the date that froze it, and an unreviewed module must have
nothing frozen. The original could only ever have been deleted.

## Blockers and exact next action

1. **The PR could not be checked or updated.** `gh` is not installed, there is
   no `GH_TOKEN`, and the GitHub MCP server failed to connect this session
   ("Authorization header is badly formatted"). The branch is pushed; the PR
   state is unknown and unmodified. A human must open or update it.
2. **No PostgreSQL and no container engine on this machine.** Standalone and
   browser evidence cannot be produced here, so STANDALONE_VERIFIED stays false
   and the evidence bundle is incomplete. CI has no M02 job yet.
3. **B00 verification remains open.** Its tracked record is still unreviewed.
4. **M01 is still `not_started` in the manifest**, deliberately: it is merged but
   nothing records its packet passing the gate. Freezing it is a separate
   decision and must not ride along with M02's.

**Next session, first action:** step 2 — guardian links and teaching
assignments. Write the tests from the frozen contract first, confirm they fail,
then implement dated many-to-many guardian visibility, staff assignments,
subject offerings and choices, and constrained relationship facts. The step-1
frontend (`frontend/src/features/registry`) is also still empty and owes the
English/Malayalam setup, directory and profile screens.

Open questions and integration cases are in `handoff.md`. No merge, no deploy.
