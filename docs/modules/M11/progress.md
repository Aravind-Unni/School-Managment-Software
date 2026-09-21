# M11 progress

| | |
|---|---|
| Phase | Implementation complete; awaiting PostgreSQL/browser evidence |
| Status | Contracts **frozen** (`school-contracts-v12`). Module code on branch. **STANDALONE_VERIFIED=false** |
| Branch | `m11/notices-third-party-sms` |
| Started from | `8d84c00da9f3378514b91adc8b98c211dc77dfc9` (`origin/main`) |
| Manifest revision | `school-contracts-v12` |
| PR | https://github.com/Aravind-Unni/School-Managment-Software/pull/12 (draft) |
| Head commit | `670c039` |
| Last recorded | 2026-09-21 |

## Original request

Build M11 notices and third-party SMS as an independently runnable standalone
module. Contracts first; then implement. May commit/push/draft PR; no merge/deploy.

## Completed behavior

- Contracts approved and frozen (`school-contracts-v12`): OpenAPI, DTO/event
  schemas, error rows, CommunicationsPort, fixtures.
- Backend: notices create/publish, enqueue/dedupe, fake SMS provider,
  timeout reconcile, signed callbacks, revocation skip, en+ml templates,
  provider secret_ref logging only.
- Frontend: composer, templates, delivery dashboard (en+ml nav/copy).
- Seeds: baseline en+ml draft notices, templates, verified/revoked contacts.
- Acceptance cases in `tests/modules/M11/` (21 passed locally on SQLite).
- `check M11 --suite contracts` green (manifest, arch 7, shared 105, M11 8).

## Incomplete / not-run

- Standalone PostgreSQL suite — not run this session (use `dev.py up`).
- Browser suite — not-run.
- PENDING integration: real SMS sandbox, real Registry contacts, real M01
  auth/2FA, production fake-adapter refusal path verification.

## Exact next step

1. `python3 scripts/dev.py up M11 --profile standalone` then migrate/seed/check
   standalone + browser when Docker/Playwright available.
2. `evidence M11`; STANDALONE_VERIFIED only after peer verify from fresh checkout.

## Blockers

None for local SQLite module tests. Container/browser evidence pending runtime.
