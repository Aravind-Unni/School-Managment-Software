# M01 access — progress

## Current phase and status

Step 5 — standalone verification / CI repair. **Not STANDALONE_VERIFIED.**
Implementation steps 1–4 exist; contract review and the whole-module exit gate
remain open. No merge or deployment is authorised.

| Item | Observed state (2026-09-19) |
|---|---|
| Branch | `m01/access-identity` |
| Session starting HEAD and remote HEAD | `d87b30dd43d89a204c685e190830245b49988cf9` |
| Current remote main | `1b01e7312e4bf4d0030c0623799863808d112ec2` |
| PR | [#2, open draft](https://github.com/Aravind-Unni/School-Managment-Software/pull/2) |
| Manifest | `school-contracts-v3-draft`; M01 `not_started`, artefacts not frozen |
| Starting worktree | Clean; continued the existing branch |

## Complete implementation

- School-scoped accounts and sessions, password challenges, session rotation,
  CSRF checking, finite throttling, 11 database tables and initial migration.
- TOTP enrolment, activation, replay protection, recovery codes and lost-device
  reset cases; encrypted seeds and hashed session/recovery credentials.
- Permission catalogue, pure deny-by-default policy, delegation bounds,
  concurrency checks, last-owner protection, audit and outbox events.
- Access frontend screens, English/Malayalam messages, generated TypeScript
  client and **eight** browser tests.
- Fifteen REST operations and proposed contract artefacts. Shared interface
  changes already on this branch remain unreviewed; see `handoff.md`.

## CI failure diagnosed and repaired

[Run 35452150849](https://github.com/Aravind-Unni/School-Managment-Software/actions/runs/35452150849)
on the starting branch revision had six successful jobs and one failed browser
job. Its log proves the stack started, migrations and seed ran, and **all eight
Access browser tests passed**. The overall result was **10 passed, 2 failed**:
Playwright also collected four M00 tests against the M01-only stack, and two
correctly failed because `/demo` is not mounted there.

The repair makes `MODULE_ID=M01` select `access.spec.ts` in Playwright and sets
that variable on the M01 CI browser step. The default collection remains all
12 tests. No test files, assertions, guards, application behaviour, shared service
interfaces, or manifest entries were changed.

For the M01 standalone stack, use:

```bash
MODULE_ID=M01 python3 scripts/dev.py check M01 --suite browser
```

The harness currently forwards its environment but does not derive this variable
from its positional module argument. The explicit variable is therefore required;
this scoped repair does not alter the shared harness.

## Verification in this session

- `doctor`: exits 2, no container engine installed.
- M00 contracts: **105 passed**; manifest and all seven architecture checks pass.
- M01 contracts: **105 shared + 16 module tests passed**, 38 module tests deselected.
- M01 SQLite module suite: **53 passed, 1 skipped** (PostgreSQL concurrency test).
- Frontend unit tests: **47 passed**; lint and TypeScript checks pass.
- Playwright discovery: M01 **8 tests / 1 file**; default **12 tests / 2 files**.
  Discovery is not browser execution.
- Local M01 standalone and browser commands: **not-run**, no running stack.
- Evidence bundle generated at
  `dev/evidence/abnvm_aumspro_1c8e30_m01/bundle.json`; incomplete because local
  standalone/browser execution is unavailable.
- Repair commit `135ee490b4e76444aa8e0be9490f5b206aa3104c`: [CI run 35453838095](https://github.com/Aravind-Unni/School-Managment-Software/actions/runs/35453838095), **all seven jobs passed**.
  PostgreSQL: **159 passed, zero skips**; Chromium against the real stack:
  **8 passed in 7.0 seconds**. Container startup, migrations and seeding passed.

## Remaining implementation and gates

Account creation/deactivation endpoints and factor-replacement REST/UI are not
implemented. Do not add them before the proposed contracts are reviewed and
frozen. Existing policy questions and shared-interface review remain open in
`handoff.md`. A second developer must verify a fresh checkout, and the human
phase exit gate must be approved before recording STANDALONE_VERIFIED.

## Concrete next action

Obtain review of the proposed M01 packet and existing shared-interface changes
on PR #2, resolve the human policy questions in `handoff.md`, then freeze the
approved contract revision before implementing new endpoints. A second developer
must verify a fresh checkout. CI repair is complete; keep the PR in draft and do
not merge or deploy. This record-only follow-up retains the tested implementation
from `135ee49`.
