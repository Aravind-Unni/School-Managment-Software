# M14 progress

| | |
|---|---|
| Phase | Contract proposal (pre-implementation) |
| Status | **AWAITING HUMAN FREEZE** — artefacts proposed; no module code |
| Branch | `m14/platform-audit-jobs-backup` |
| Branched from | `a2f16c24dc6a7c7004e5358a094f0bd0fc5760dd` (`origin/main`) |
| Manifest revision | `school-contracts-v14` (proposed freeze → `v15`) |
| PR | (set after draft PR opens) |
| Last recorded | 2026-09-21 |

## Original request

Build M14 Audit / jobs / deployment / backup / observability as an independently
runnable standalone profile. Inspect contracts first, propose missing schemas
for review, then implement. Do not invent school policy. Delivery may commit,
push, and open a draft PR; do not merge or deploy.

## Completed behaviour

- Inspected checkout, git state, `contracts/manifest.json` (`M14` was
  `not_started` with empty artefacts), PACKET, foundation `PlatformPort`,
  common audit/event schemas, FakePlatform rules.
- Proposed full contract packet under `contracts/M14/`:
  OpenAPI, DTOs, events, error codes, ports, review-decisions, fixtures.
- Updated `dev/modules/M14/module.json` to require object storage for backup
  acceptance (proposed; aligns with review item 14).

## Incomplete behaviour

- Human freeze of contracts (items 1–16 in `review-decisions.md`).
- Implementation steps 1–4 (audit/outbox/jobs; registration/CI;
  deployment/monitoring; backup/load/restore).
- Standalone / contracts / browser suites; evidence; STANDALONE_VERIFIED.

## Changed interfaces (proposed only — not frozen)

- Public API under `/api/v1`: `health/live`, `health/ready`, `jobs/{id}`,
  `jobs/{id}/retry`, `audit`, `operations/restore-rehearsals`.
- Permissions: `platform.read_health`, `jobs.read`, `jobs.retry`, `audit.read`,
  `backups.manage`.
- Events: `platform.job_state_changed`, `platform.restore_rehearsal_verified`.
- Frozen `PlatformPort` signatures **unchanged**; ergonomic facades are
  module-local.

## Exact next step

1. Reviewer approves or amends `contracts/M14/review-decisions.md`.
2. Freeze artefacts in `contracts/manifest.json` under `school-contracts-v15`
   (`frozen: true`, named reviewer + date).
3. Only then implement step 1: audit / outbox / jobs models + real PlatformPort
   binding + sample producer/consumer tests.

## Blockers

- **Human contract review gate** — AGENTS.md forbids coding before freeze.
- PENDING integration (do not claim in standalone): real domain job identities,
  production monitoring, full-scale RPO/RTO, real M01 auth/2FA.
