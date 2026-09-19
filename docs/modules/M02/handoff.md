# M02 handoff

## Read first

The contract gate is **closed**: the packet was approved and frozen under
revision `school-contracts-v4` on 2026-09-20. **Step 1 of 4 is implemented and
passing.** Steps 2-4 and the whole frontend are outstanding.

Read [progress.md](progress.md) first — it lists every check actually run and
every test that was changed. Then the [packet](../../../contracts/M02/PACKET.md)
and [review decisions](../../../contracts/M02/review-decisions.md).

Do not mistake the SQLite test profile for standalone verification. This machine
has no PostgreSQL and no container engine, so the standalone and browser suites
recorded `not-run`, and STANDALONE_VERIFIED is false.

Session source: branch `m02/registry-contracts` at
`faeb9a2555a8639c33240ebf94da4d8c5a893345`, four commits ahead of main
`1d17113ea333b1c77743b6cfdfe3b3d2314089f1`; revision `school-contracts-v4`.

## What is available

The frozen REST surface, DTOs, error rows, four event payloads, service
signatures and synthetic structural fixtures — plus, now, a running step-1
implementation of the configuration and people half of it.

Serving today: `school-config`, `academic-years`, `terms`, `standards`,
`sections` (with archive), `subjects`, `students` (list, admit, read, amend),
`students/duplicate-review`, `guardians`, `staff`. Eleven tables, migrations
with no drift, and a bootstrap that installs the one SchoolConfig row.

NOT serving, and deliberately not mounted: guardian links, subject offerings and
enrolments, teaching assignments, enrolment, transfer, withdrawal, promotion and
exchange. Mounting an empty route would let a consumer call something that
silently does nothing.

Fixture data uses two schools, two active years, C1/C2, S1's dated transfer, G1
linked to two children, multiple guardians for S1 and disjoint optional subjects.
These files are not installed runtime seeds or production school data.

## Contract revision items found by implementing

These are real disagreements between frozen artefacts, found by building against
them. None was resolved by editing a frozen file.

1. **Trailing slashes.** `contracts/M02/openapi.json` declares every path without
   one (`/students`). The shared `API_PATH_ROOT_PATTERN` in
   `backend/contracts/registration.py` requires every declared ROOT to end in one
   (`students/`). So `registration.py` declares `students/` while `urls.py`
   serves `students`, and the bare path is therefore outside the namespace the
   host's collision check actually examines. Serving both forms was tried and
   reverted: it produced duplicate operationIds and failed
   `spectacular --fail-on-warn`. Reconciling the two is a contract revision.
2. **`SPECTACULAR_SETTINGS["VERSION"]` is still `school-contracts-v3-draft`.**
   It was left alone on purpose: CI diffs the generated M00 schema against the
   frozen `contracts/M00/openapi.yaml`, so changing the version string would
   break that check against a frozen artefact. Moving it to track
   `contracts/revision.json` needs M00's schema re-frozen in the same revision.
3. **M01 is `not_started` in the manifest while being merged and live.** Its
   artefacts are hashed so drift is caught, but nothing claims they are approved.
   Closing that gap is a separate reviewed decision.

## Decisions still to obtain

- B00 prerequisite verification and independent review are unresolved in tracked
  records. Do not silently mark B00 complete because M01 was merged.
- Promotion proposal: staff-reviewed explicit destinations, including repeat-year
  exceptions, without automatic marks/pass logic. Await school confirmation.
- Adult guardian access proposal: leave policy unpublished until school-approved;
  no inferred age threshold or automatic transition. Await school confirmation.
- Review duplicate matching, visibility vocabulary, allowed withdrawal outcome
  mappings and supplied reference data. No approved CBSE curriculum/rules exist.
- Review 300-second step-up and 15-minute preview windows, synchronous bulk
  operations and a durable withdrawal access-review task (no worker claimed).
- Confirm capability issuance and trusted account-person association with the
  host/M01 owner. A dataclass or UUID passed from a browser is not authority.

The two plain-language policy questions were asked while preparing the draft;
no answer was received before this handoff. Draft proposals are not consent.

## Traps exposed by reading current code

Items 3 and 6 are now RESOLVED; the rest still stand.

1. The frozen event_type regex allows lowercase module.event, not the requested
   `StudentEnrolled.v1` family. Do not silently rename events or change the regex.
   Step 1 emits no events, so this is still untouched and still open.
2. Registry DTOs already exist. StudentDTO has no version; use the versioned
   browser StudentRecord without breaking its internal shape. Step 1 does exactly
   this: `POST /students` returns the five-field StudentDTO, and a follow-up GET
   returns the versioned record. Keep them separate.
3. **RESOLVED.** `shared/ports/bindings.py` now loads a module's own
   `fixture_policy.py` into the fake, so grants are enumerated per action rather
   than bypassed. `FIXTURE_POLICY_RULES` has no wildcard and a contract test
   asserts it never grows one.
4. ScopeResolver's plural-to-singular choice and school check require review;
   do not use an arbitrary first subject to authorize a different elective.
5. Current Platform writes DTOs and returns None; start_job is absent. No eager
   replacement or invented successful job result is permitted.
6. **RESOLVED.** The manifest generator reads `contracts/revision.json` and
   discovers artefacts recursively. It had never hashed five contract files,
   listed in progress.md. Check that list before assuming any older "manifest
   green" result covered what you think it did.
7. Browser discovery is not module-generic yet. M02's approved runner/browser
   registration must select its own tests, preserving other modules' tests.
8. Withdrawal dates must govern rosters, not today's status. Do not erase history
   or change current status immediately for a future-effective withdrawal.

## How to run what exists

Module suite and contract suite, on the SQLite test profile — this is the loop
step 1 was developed against, and it is NOT standalone verification:

```bash
MODULE_ID=M02 .venv/bin/python -m pytest tests/modules/M02 -q   # 39 tests
python3 scripts/dev.py check M02 --suite contracts               # 105 + 12
```

The frozen artefacts alone, with no database and no app:

```bash
MODULE_ID=M02 .venv/bin/python -m pytest tests/modules/M02/test_contracts.py -q
```

Schema generation, which CI will gate once M02 has a job:

```bash
MODULE_ID=M02 DJANGO_SETTINGS_MODULE=config.settings.test_sqlite PYTHONPATH=backend \
  .venv/bin/python backend/manage.py spectacular --fail-on-warn --file /tmp/m02.yaml
```

None of the above validates PostgreSQL behaviour, real concurrency, migrations
against a real empty and seeded database, or any browser journey.

## Standalone verification — still owed

`dev.py up M02` needs a container engine; this machine has none, and no local
PostgreSQL either, so `doctor` exits 2. `check --suite standalone` and
`--suite browser` both recorded `not-run`, and `evidence M02` reports an
incomplete bundle. That is the honest state; do not read the SQLite numbers as
satisfying it.

Still owed before the module can be called verified: real PostgreSQL with
migrations on empty and seeded databases, the browser suite in both locales, a
production frontend build, a CI job for M02, and a second developer's
fresh-checkout verification.

The local profile serves a server-fixed synthetic persona with fake Access and
the real Registry. There is no M01 login integration and no identity header is
ever accepted — the shared transport rejects them outright.

## Integration remains PENDING

- M03 central timetable subject-period consumers.
- M04 per-period attendance and retained historical rosters/results after transfer.
- M10 alumni candidates after leaving events.
- M01 account/guardian access review and withdrawal revocation.
- M13 actual domain exchange consumer.

Synthetic consumer fixture checks do not execute any of those real modules.
Second-developer verification and the whole-module exit gate remain required.
