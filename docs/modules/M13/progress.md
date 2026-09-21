# M13 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting PostgreSQL/browser evidence |
| Branch | `m13/reports-imports-exports` |
| Started from | `3d0b03bbae4d7509ec5c27ef8e4a029d4eebdf13` (`origin/main`) |
| Manifest revision | `school-contracts-v14` (M13 **frozen**) |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/14 |
| Last recorded | 2026-09-21 |

## Original request

Build M13 exchange (imports, exports, report cards) as an independently runnable
standalone profile: real Django/React/PostgreSQL/migrations, deterministic fakes
for other business modules, contracts first, then implement and test. Delivery
may commit, push, and open a draft PR; do not merge or deploy.

## Completed behavior

- Contracts frozen: OpenAPI, DTO/event schemas, error codes, ports, fixtures.
- Domain adapter registry (enrolments, balances, results, loans, export datasets).
- Import validate → commit with digest check, Idempotency-Key, chunked resume.
- Exports with field grants and formula neutralization; report cards with immutable
  revision binding and supersession; Malayalam text in PDF metadata/content.
- Frontend routes: `/imports`, `/exports`, `/reports`, `/report-cards`.
- Module SQLite suite: **47 passed**. Contracts suite green via `dev.py check`.

## Incomplete behavior

- Standalone PostgreSQL / Compose stack: **not-run** (no container engine).
- Browser suite: **not-run**.
- Real domain adapters, balances/loans reconciliation, real artifact ACLs: **PENDING**.

## Changed interfaces

- Frozen: `ExchangePort` in `backend/contracts/exchange.py`.
- REST under `/api/v1` path roots `imports/`, `import-templates/`, `exports/`,
  `reportcards/`, `reports/`.
- Permissions: `imports.validate|commit`, `reports.read|export`, `reportcards.generate`.

## Exact next step

1. Commit and push; open draft PR.
2. On a machine with Docker: `up` / `migrate` / `seed` / `check --suite standalone`
   and browser; record evidence; only then set `STANDALONE_VERIFIED`.

## Blockers

Container engine absent on this machine (`doctor` exit 2). Standalone/browser
evidence cannot be claimed until that path runs.
