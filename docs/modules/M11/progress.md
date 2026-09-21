# M11 progress

| | |
|---|---|
| Phase | Contract proposal — awaiting human review gate |
| Status | Artefacts proposed; **not frozen**; **no module code** |
| Branch | `m11/notices-third-party-sms` |
| Started from | `8d84c00da9f3378514b91adc8b98c211dc77dfc9` (`origin/main`) |
| Manifest revision | `school-contracts-v11` (current); proposed freeze `school-contracts-v12` |
| PR | (pending) |
| Head commit | `cd2b8322f96df1b938fa1a3398b049c1e07e6200` |
| Last recorded | 2026-09-21 |

## Original request

Build M11 notices and third-party SMS as an independently runnable standalone
module. Inspect contracts first, propose missing schemas for review, then
implement. May commit/push/draft PR; no merge/deploy.

## Completed behavior

- Branch from latest `origin/main`.
- Proposed OpenAPI, DTO/event schemas, error rows, ports.md, consumer fixtures,
  review-decisions (18 items).

## Incomplete behavior

- Human review / freeze of contracts.
- Steps 1–4 implementation (notices → adapter → callbacks → bilingual templates).
- Standalone / contracts / browser suites; evidence; STANDALONE_VERIFIED.

## Changed interfaces (proposed, not applied)

- New `CommunicationsPort.enqueue` (after freeze).
- Possible revision of shared `NotificationPort` (review item 3).
- Module-local `SmsProviderPort` (not shared).

## Exact next step

1. Reviewer approves or revises `contracts/M11/review-decisions.md` items 1–18.
2. On approval: set revision `school-contracts-v12`, freeze hashes, add
   `backend/contracts/communications.py`.
3. Then implement step 1 (Notices) only.

## Blockers

**Human gate:** contract packet must be reviewed before any module coding or
tests. Shared `NotificationPort` change (item 3) needs an explicit decision.
