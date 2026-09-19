# M02 Academic registry and student lifecycle

**Contract approved and frozen. Step 1 of 4 implemented; STANDALONE_VERIFIED is
false.**

- [Progress and next action](progress.md)
- [Handoff and blockers](handoff.md)
- [Acceptance/evidence record](acceptance.json)
- [Approved contract packet](../../../contracts/M02/PACKET.md)
- [Review outcome and open decisions](../../../contracts/M02/review-decisions.md)

M02 owns people, academic references, dated guardian/staff relationships, class
and subject enrolments, transfers, promotion, withdrawal and validated exchange.
It runs independently with the real Registry and deterministic Access and
Platform dependencies. No other business module is integrated by this task.

Serving today (step 1): school configuration, academic years, terms, standards,
sections, subjects, students, guardians, staff, and the duplicate-review gate on
admission. Guardian links, enrolment, promotion, withdrawal and exchange are
steps 2 to 4 and are deliberately not mounted.

The packet was approved on 2026-09-20 and frozen under revision
`school-contracts-v4`. Changing any file in `contracts/M02` now moves a frozen
hash and fails `contract_manifest.py --check`; that is a new reviewed revision,
not an edit.

Step-1 numbers come from the SQLite test profile. This machine has no container
engine and no PostgreSQL, so the standalone and browser suites recorded
`not-run` and the evidence bundle is incomplete. Read `progress.md` before
treating any of it as verification.
