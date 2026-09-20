# M04 progress — teacher attendance and corrections

## Original request

Build M04 independently: per-period attendance from the central timetable,
draft/submit/correct, period summaries, events, en/ml UI, standalone profile,
evidence and a draft PR. Propose contracts for review first.

## Current phase / source identity

**Phase: implementation complete through steps 1–4 locally; browser suite depends
on a running stack / CI. STANDALONE_VERIFIED is false until second-developer
verification.**

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m04/teacher-attendance` |
| Branched from | `fd7751d` (`origin/main`) |
| Manifest revision | `school-contracts-v5`, M04 **frozen** |
| PR | Draft #5 — https://github.com/Aravind-Unni/School-Managment-Software/pull/5 |
| Recorded | 2026-09-20 |

## Complete

- Contract gate: all nine review items approved; TimetablePort + AttendancePort
  added to shared contracts; FakeTimetable + M04 registry overlay.
- Step 1: Session/Entry models, periods list, create/save drafts, period-teacher
  gate, elective roster rejection.
- Step 2: Submit with Idempotency-Key, concurrency, roster_stale; React mark UI
  en/ml (submitSucceeded only after success).
- Step 3: Corrections + events; real reconcile helper preserving history;
  summaries from timetable eligibility (percentage null).
- Step 4: Playwright attendance.spec.ts; contract tests; handoff/acceptance.

## Incomplete / honest gaps

- Browser suite not claimed green until observed against a real stack.
- STANDALONE_VERIFIED false (no second-developer fresh checkout).
- PENDING integration: real roster transfers, substitutions, notifications,
  performance denominators.

## Exact next step

Push, update draft PR, run `dev.py check M04` suites in CI / with containers.
Second developer verifies from a fresh checkout before STANDALONE_VERIFIED.
