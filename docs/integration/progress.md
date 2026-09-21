# Integration progress — C02

| | |
|---|---|
| Phase | C02 — connect independently verified modules |
| Branch | `c02/integration` |
| Started from | `63bbbca86e1bb771234487ba166631d275bd7ac5` (`origin/main`, M14 merge #15) |
| Tip (this branch) | see `git rev-parse HEAD` after push |
| Contract revision | `school-contracts-v15` (status `reviewed`) |
| `INTEGRATION_VERIFIED` | **false** — required journeys / browser / load / restore not complete |
| `RELEASE_ACCEPTED` | **false** |
| Independent approvals | **0 / 14** (`STANDALONE_VERIFIED`) |
| Last recorded | 2026-09-21 |

Exact inventory: [`release-manifest.json`](release-manifest.json). Continue via [`handoff.md`](handoff.md).

---

## Suites (executed this session)

| Suite | Status | Evidence |
|---|---|---|
| contracts (`check ALL`) | **passed** (manifest + arch + 105 contract tests) | `dev/evidence/..._all/contracts.json` |
| integration (`check ALL`) | **passed** (244 pytest) | `dev/evidence/..._all/integration.json` |
| browser | **not-run** | no container engine (`doctor` exit 2) |
| load | **not-run** | executor records not-run (not passing) |
| restore | **not-run** | executor records not-run (not passing) |

## What landed on this branch

- Inventory + release manifest + M01 conflict report + migration-order notes
- Integrated host: `APPROVED_MODULE_IDS` full assembly order, collision check, real port binder under `backend/config/real_ports.py`
- `dev.py` supports `ALL` + suites `integration|load|restore`
- M02 steps 2–3: lifecycle models, migration `0002`, REST, **real `RegistryPort`**
- Integration seed scenario for `seed all --scenario integration`
- Controlled sandbox notifications + host object-storage adapter (no shared→module imports)

## Hard blockers remaining

1. M01 contracts still `not_started` — see [`m01-contract-conflict.md`](m01-contract-conflict.md)
2. 0/14 `STANDALONE_VERIFIED`
3. No Docker daemon — cannot run `up all`, browser, worker crash/retry, load, restore
4. Full C02 journey matrix not executed on a live integrated stack
5. M02 step 4 (promotion/withdrawal/exchange polish) still open

## Next session — concrete first action

1. Install/start a container engine; `python3 scripts/dev.py doctor` must exit 0.
2. Then:
   ```bash
   python3 scripts/dev.py up all --profile integrated
   python3 scripts/dev.py migrate all --profile integrated
   python3 scripts/dev.py seed all --scenario integration
   python3 scripts/dev.py check all --suite browser
   ```
3. Drive required real journeys; only then consider `INTEGRATION_VERIFIED`.

Do not merge or deploy. Do not silent-freeze M01.
