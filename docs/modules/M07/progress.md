# M07 progress

| | |
|---|---|
| Phase | Contract proposal — awaiting human freeze |
| Status | Artefacts proposed under `contracts/M07/`. **Not frozen. No implementation yet.** |
| Branch | `m07/fees-payments-balances-receipts` |
| Started from | `da0570c2efdd3e17ef852164d0a62a9265416fbf` (`origin/main`) |
| Manifest revision | `school-contracts-v7` (current); proposed freeze → `school-contracts-v8` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/8 (draft) |
| Head commit | `768542a416a2f9ea1fcdb85fa7698e5bbf9111f9` |
| Last recorded | 2026-09-20 |

## Original request

Build M07 fees, payments, balances and receipts as an independently runnable
standalone module. Inspect contracts first, propose missing schemas for review,
then implement. May commit/push/draft PR; no merge/deploy.

## Completed behavior

- Source identity recorded (branch from latest main including M06).
- Full contract proposal: OpenAPI, DTO/event schemas, error rows, `FeesPort`
  signatures, consumer fixtures, acceptance cases, review-decisions (12 items).

## Incomplete behavior

- Human review / freeze of items 1–12 in `contracts/M07/review-decisions.md`
- Implementation steps 1–4 (charge ledger → payments → corrections → bus/reconcile UI)
- Suites, evidence, STANDALONE_VERIFIED

## Changed interfaces (proposed only)

- Additive `FeesPort` + fee DTOs in `backend/contracts` (not yet coded)
- New `contracts/M07/*` artefacts (not yet in manifest freeze)

## Exact next step

1. Reviewer answers yes/no on the 12 items in `review-decisions.md`
2. On approval: freeze under `school-contracts-v8`, run
   `python3 scripts/contract_manifest.py --update`, then implement step 1
   (charge ledger)

## Blockers

- **Human gate:** contract packet must be reviewed before coding (AGENTS.md).
- Deferred policy (not freeze blockers): late fees, bus proration, concession
  authority matrix — need signed school examples; baseline omits automation.
