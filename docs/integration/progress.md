# Integration progress — C02

| | |
|---|---|
| Phase | C02 — connect independently verified modules |
| Branch | `c02/integration` |
| Started from | `63bbbca86e1bb771234487ba166631d275bd7ac5` (`origin/main`, M14 merge #15) |
| Contract revision | `school-contracts-v15` (status `reviewed`) |
| `INTEGRATION_VERIFIED` | **false** — not claimed |
| `RELEASE_ACCEPTED` | **false** — not claimed |
| Independent approvals | **0 / 14** (`STANDALONE_VERIFIED`) |
| Last recorded | 2026-09-21 |

Exact inventory: [`release-manifest.json`](release-manifest.json). Continue via [`handoff.md`](handoff.md).

---

## Current status

**Inventory complete.** Host wiring and real adapters are the next work. No suite gate has been marked passed on this branch without execution.

### Hard blockers (do not ignore)

1. **M01 contracts unfrozen** — code on `main`, manifest `not_started`.
2. **M02 step 1 of 4** — no `RegistryPort`; no guardian links / assignments / enrolments.
3. **0/14 `STANDALONE_VERIFIED`**.
4. Integrated profile still scaffold-only until wiring commits land (`APPROVED_MODULE_IDS = ("M00",)` at inventory).

### Suites (honest)

| Suite | Status |
|---|---|
| contracts | not-run |
| integration | not-run |
| browser | not-run |
| load | not-run |
| restore | not-run |

---

## What is done on this branch

- [x] Branch `c02/integration` from current `main`
- [x] `docs/integration/release-manifest.json` from PR merge commits + code verification
- [x] `docs/integration/progress.md` / `handoff.md`
- [ ] Real port binder + expand `APPROVED_MODULE_IDS`
- [ ] `dev.py` `up/migrate/seed/check/evidence all`
- [ ] M02 RegistryPort + steps 2–3 (separately reviewed commits)
- [ ] M01 contract conflict report (no silent freeze)
- [ ] Execute suites; draft PR

---

## Next session — concrete first action

1. Implement `backend/shared/ports/real_bindings.py` and grow `integrated.py`.
2. Fix `urls.py` to union consumers and assert registration collisions.
3. Extend `scripts/dev.py` for `all` + integration/load/restore suites.
4. Then M02 `RegistryPort` (blocking).

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py check all --suite contracts
```

Do not set `INTEGRATION_VERIFIED` until required real workflows pass under executed suites.
