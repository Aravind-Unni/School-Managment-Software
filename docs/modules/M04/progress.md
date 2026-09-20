# M04 progress — teacher attendance and corrections

## Original request

Build M04 independently: per-period attendance from the central timetable,
draft/submit/correct, period summaries, events, en/ml UI, standalone profile,
evidence and a draft PR. Propose contracts for review first. Do not integrate
other business modules, invent school policy, merge or deploy.

## Current phase / source identity

**Phase: contract proposal only — AWAITING HUMAN REVIEW before any
implementation or freeze.**

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m04/teacher-attendance` |
| Branched from | `fd7751dbbeddfbcd3a526ad244a6e8fe0638a892` (`origin/main`) |
| Manifest revision | `school-contracts-v4` (unchanged; M04 still `not_started` in manifest) |
| PR | **Draft #5** — https://github.com/Aravind-Unni/School-Managment-Software/pull/5 |
| Head | `e4ec862` |
| Recorded | 2026-09-20 |

## Complete

- Inspected checkout, branched from latest `main` (M03 merged).
- Read packet, shared ports, M03 TimetableService/DTOs, FakeRegistry enrolments.
- Proposed contract artefacts under `contracts/M04/` (OpenAPI, DTOs, events,
  errors, ports, fixtures, review-decisions). **Not frozen.**

## Incomplete

- Human review / freeze of M04 contracts.
- Shared revision: `TimetablePort` + `AttendancePort` in `backend/contracts`.
- Implementation steps 1–4.
- Standalone / browser / evidence.
- PENDING integration cases (real roster transfers, substitutions, notifications,
  performance denominators).

## Changed interfaces

None frozen. Proposal only — see `contracts/M04/review-decisions.md`.

## Exact next step

Reviewer answers the nine items in `review-decisions.md`. On approval: freeze
M04 in `revision.json`, run `contract_manifest.py --update`, then implement
step 1 (resolve periods/rosters, create drafts).

## Blockers

**Contract review gate.** AGENTS.md forbids coding before freeze.
