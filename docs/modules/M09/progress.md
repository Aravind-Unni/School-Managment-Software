# M09 progress

| | |
|---|---|
| Phase | Contract proposal — **human review gate** |
| Status | Artefacts proposed; **not frozen**; no module code yet |
| Branch | `m09/library-catalogue-lending` |
| Started from | `b046ad6e567e3a1e6d165d17ffd101c3821300be` (`origin/main`) |
| Manifest revision | `school-contracts-v9` (current); proposed freeze `school-contracts-v10` |
| PR | none yet |
| Head commit | (local proposal) |
| Last recorded | 2026-09-21 |

## Original request

Build M09 library catalogue lending and returns as an independently runnable
standalone module. Inspect contracts first, propose missing schemas for review,
then implement. May commit/push/draft PR; no merge/deploy.

## Completed behaviour

- Contract proposal written under `contracts/M09/`: OpenAPI, DTO/event schemas,
  error rows, ports.md, fixtures, review-decisions.md (items 1–18 proposed).

## Incomplete

- Human approval of review-decisions (especially permissions split, fixture
  borrower limits, overdue-on-GET vs worker).
- Freeze to `school-contracts-v10` + `backend/contracts/library.py`.
- Implementation steps 1–4, tests, evidence.

## Changed interfaces

None frozen. Proposed: `LibraryPort`, REST under `/api/v1/library/...`.

## Exact next step

1. Reviewer approves or amends `contracts/M09/review-decisions.md`.
2. Freeze revision; then implement catalogue → issue/return → renew/overdues →
   imports/borrower UI.

## Blockers

Waiting on human contract review (AGENTS.md gate).
