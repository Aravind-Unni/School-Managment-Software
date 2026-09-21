# Integration progress — C02

| | |
|---|---|
| Phase | C02 — production install path |
| Branch | `c02/path-collision-fix` |
| Contract revision | `school-contracts-v15` |
| `INTEGRATION_VERIFIED` | **false** (human gates remain) |
| `RELEASE_ACCEPTED` | **false** (needs VPS + school/ops) |
| Independent approvals | **0 / 14** — see `peer-verification.md` |
| Last recorded | 2026-09-21 |

## Suites (observed on ALL integrated)

| Suite | Status | Evidence |
|---|---|---|
| contracts | passed | prior / re-run as needed |
| integration | passed | prior |
| browser | **passed** (5 integrated-smoke) | `dev/evidence/..._all/browser.json` |
| load | **passed** | `dev/evidence/..._all/load.json` |
| restore | **passed** | `dev/evidence/..._all/restore.json` |

## Delivered this branch

- Phase 0: path collisions, Vite `/api` proxy, SCHOOL_ID, seed, readyz
- Phase 1: `production.py` full assembly; `infra/prod/` compose+nginx+gunicorn+runbook; `bootstrap_owner`
- Phase 2: session shell, permission nav, CSRF client, role home
- Phase 3: registry UI + API pages for former stubs; `generate:client` for modules whose OpenAPI bundles
- Phase 4: peer protocol doc; **no** silent M01 freeze; STANDALONE_VERIFIED stays false
- Phase 5: load/restore executors; integrated browser smoke; journey matrix tracked
- Phase 6: prod pack + release checklist; deploy awaits operator VPS credentials

## Honest blockers (cannot invent)

1. Named peer verifier for 14 standalone re-runs
2. Human M01 contract freeze review
3. VPS SSH, domain, TLS email, SCHOOL_ID for campus
4. School contact + ops signatures on `release-checklist.md`
5. Real school data import source (or empty start via UI)

## Next session

1. Operator supplies verifier name + VPS access
2. Peer fills `peer-verification.md`; freeze M01 after review
3. Deploy `infra/prod` per RUNBOOK; school smoke; set RELEASE_ACCEPTED only when signed
