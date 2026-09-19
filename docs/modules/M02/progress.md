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

**Phase: contract proposal. Status: awaiting human review and prerequisites.**
Implementation steps 1–4 have NOT begun. STANDALONE_VERIFIED is false.

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m02/registry-contracts` |
| Starting main | `1d17113ea333b1c77743b6cfdfe3b3d2314089f1` |
| Prior task | M01 PR #2 merged; no open M02 PR existed at session start |
| Starting worktree | Clean; branched from freshly fetched `origin/main` |
| Manifest revision | `school-contracts-v3-draft`, unchanged |
| M02 manifest status | `not_started`, no approved/frozen artefacts |
| PR | Draft PR to be opened after committing this proposal |
| Recorded | 2026-09-19 |

## Complete in this phase

- Read repository rules, foundation progress/handoff/acceptance, target placeholders,
  shared DTO/Protocol/error/event schemas, registration, resolver, fake/binding
  interfaces, harness, existing tests and pinned dependency declarations/locks.
  No separate ADR files were found; architecture decisions are in the existing
  foundation records and source docstrings.
- Authored an explicit proposal: OpenAPI 3.1 with **81 operations / 53 paths**,
  **100 DTO/request/page shapes**, **4 event payload schemas**, **32 error rows**,
  current/proposed service signatures, deterministic synthetic scenarios, eight
  DTO response examples and twenty proposed acceptance cases.
- Defined dated subject enrolment and elective-period examples around transfer
  date 2030-09-01. Full-class fallbacks for subject rosters are prohibited.
- Identified shared capability, account/person binding, event-name, fixture-binding,
  scope-resolver and exchange gaps without modifying their runtime contracts.
- Recorded proposed school-dependent decisions as unapproved. No policy activated.

## Observed checks (not implementation evidence)

| Command/check | Result |
|---|---|
| `python3 scripts/dev.py doctor` | Exit 2: no container engine |
| Startup `check M00 --suite contracts` | PASS: 105 tests; 7 architecture checks; 13 frozen entries |
| Draft OpenAPI validation using installed drf-spectacular | PASS: 81 operations |
| Draft JSON Schema validation using installed jsonschema | PASS: DTO and event schema documents |
| Schema validation of response fixtures | PASS: 8 examples, including elective rosters |
| Operation IDs and top-level closed write shapes | PASS |
| `check M02 --suite contracts` | FAIL: unreviewed new artefacts absent from manifest; shared 105 tests and architecture pass |
| `check M02 --suite standalone` | Exit 3: no M02 registration/implementation |
| `check M02 --suite browser` | Exit 2: no running stack |
| `evidence M02` | Exit 1: incomplete bundle; not verified |

The first ad-hoc OpenAPI validation attempt lacked Django settings; configuring
only the renderer settings fixed that invocation, with no schema/runtime changes.
The manifest failure is expected for an unapproved proposal. Do not alter a test,
weaken the guard, move files out of its reach or mark the proposal frozen to hide it.

## Incomplete behaviour and changed interfaces

No Registry backend/frontend, migrations, real profile registration, runtime seed,
module test files or live URLs yet. Every requested implementation step remains.
Only M02 contract/docs files are changed. `backend/contracts`, shared runtime,
manifest, fakes, CI, other modules and dependency locks remain unchanged.
The proposed new ports/security boundaries and compatibility choices are listed
in `contracts/M02/review-decisions.md`; none are approved by this branch.

## Blockers and exact next action

1. Review the packet and decisions, including promotion-by-explicit-destination,
   unpublished adult guardian policy, duplicate criteria, subject-choice transfer,
   synchronous imports/promotion and the proposed 2FA/preview windows.
2. Resolve B00 verification: its tracked record remains unreviewed/unverified.
   M01's green stack does not certify the entire foundation. Local engine absent.
3. Approve the required shared revision and freeze the actual M02 artefacts.
   Current manifest tooling hardcodes the revision and M00-only freeze, and misses
   nested module schemas; correcting that requires explicit shared review.
4. Only then write step-1 tests and implement configuration/people, continuing
   through steps 2–4 with per-step progress and real PostgreSQL/browser evidence.

Open questions and integration cases are in `handoff.md`. No merge or deployment.
