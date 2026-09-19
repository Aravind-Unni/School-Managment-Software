# M02 handoff

## Read first

This is a **proposal-only branch**, not a runnable Registry module. Read
[progress.md](progress.md), then the [packet](../../../contracts/M02/PACKET.md)
and [review decisions](../../../contracts/M02/review-decisions.md).
Do not mistake schema validation or the foundation's tests for M02 behaviour.

Session source: clean current main `1d17113ea333b1c77743b6cfdfe3b3d2314089f1`;
branch `m02/registry-contracts`; revision `school-contracts-v3-draft`.
M01's former branch was merged, so this task uses a fresh branch.

## What is available

A complete proposed REST surface, DTOs, error rows, four event payloads, explicit
service signatures, synthetic structural fixtures and a review list. Proposed
fixtures use two schools, two active years, C1/C2, S1's dated transfer, G1 linked
to two children, multiple guardians for S1 and disjoint optional subjects.
These files are not installed runtime seeds or production school data.

## Decisions to obtain before code/tests

- B00 prerequisite verification and independent review are unresolved in tracked
  records. Do not silently mark B00 complete because M01 was merged.
- Approve/revise M02's packet and required shared interfaces, then freeze a new
  reviewed revision. Manifest drift currently names the newly proposed files.
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

1. The frozen event_type regex allows lowercase module.event, not the requested
   `StudentEnrolled.v1` family. Do not silently rename events or change the regex.
2. Registry DTOs already exist. StudentDTO has no version; use the proposed
   versioned browser StudentRecord without breaking its internal shape.
3. Current FakeAccess permits module extra_rules in tests, but the host factory
   does not pass them. Rules also lack actor/section-specific grants. A module
   test-only fake would not prove the independently running profile works.
4. ScopeResolver's plural-to-singular choice and school check require review;
   do not use an arbitrary first subject to authorize a different elective.
5. Current Platform writes DTOs and returns None; start_job is absent. No eager
   replacement or invented successful job result is permitted.
6. Manifest tooling cannot freeze a new module/revision correctly without a
   reviewed adjustment and does not currently enumerate nested module schemas.
7. Browser discovery is not module-generic yet. M02's approved runner/browser
   registration must select its own tests, preserving other modules' tests.
8. Withdrawal dates must govern rosters, not today's status. Do not erase history
   or change current status immediately for a future-effective withdrawal.

## Reproduce proposal validation (no module test suite)

Use the installed hash-pinned dependencies; no new package is required:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from django.conf import settings
from drf_spectacular.validation import validate_schema
from jsonschema import Draft202012Validator, FormatChecker
settings.configure()
p = Path('contracts/M02')
s = json.loads((p/'schemas/dtos.schema.json').read_text())
Draft202012Validator.check_schema(s)
Draft202012Validator.check_schema(json.loads((p/'schemas/events.schema.json').read_text()))
validate_schema(json.loads((p/'openapi.json').read_text()))
for example in json.loads((p/'fixtures/responses.json').read_text()):
    selected = {'$defs': s['$defs'], '$ref': '#/$defs/' + example['schema']}
    Draft202012Validator(selected, format_checker=FormatChecker()).validate(example['value'])
print('Draft schemas and eight response examples validate; no M02 behaviour executed.')
PY
```

This does not validate database invariants, authorization or concurrent writes.
Module tests are intentionally not authored before the packet gate.

## Startup and review after implementation

Commands are listed in acceptance.json. Currently `up`/`migrate`/`seed` cannot run
M02 because registration.py is absent. No URL was printed or assumed. Ports will
come from `up`; there are no working M02 login instructions yet. The future local
profile uses a server-fixed synthetic persona, fake Access with approved explicit
grants and the real Registry. No arbitrary identity headers and no real M01 login
integration. Use two browser locales and the real backend for success/denial,
loading/error/empty-state journeys, not request mocks.

No migrations exist yet, therefore no empty/populated migration verification or
irreversible-operation claim can be made. No worker/broker is proposed; adding a
job requires reviewed contracts and real worker testing.

## Integration remains PENDING

- M03 central timetable subject-period consumers.
- M04 per-period attendance and retained historical rosters/results after transfer.
- M10 alumni candidates after leaving events.
- M01 account/guardian access review and withdrawal revocation.
- M13 actual domain exchange consumer.

Synthetic consumer fixture checks do not execute any of those real modules.
Second-developer verification and the whole-module exit gate remain required.
