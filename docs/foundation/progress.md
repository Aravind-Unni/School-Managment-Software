# Foundation progress — B00

**Status: complete, CI green end to end, awaiting peer review.** Not merged, not
deployed.

| | |
|---|---|
| Phase | B00 — shared development foundation |
| Branch | `b00/shared-foundation` |
| Started from | `d0df19de0e7172ea22fd0a85eed99dfe41e04ad9` (`main`, contained only `README.md`) |
| Contract revision | `school-contracts-v3-draft` (status `draft`) |
| Modules implemented | `M00` placeholder only. **None of M01–M14.** |
| Last recorded | 2026-09-19 |

Exact outcomes, source identity and the verified/unverified split live in
[`acceptance.json`](acceptance.json). Read
[`handoff.md`](handoff.md) before starting work.

---

## What is built

| Area | State |
|---|---|
| Repository layout | Complete, matching the B00 packet, including all 14 module directories |
| Lockfiles | `backend/requirements*.txt` hash-pinned via `uv`; `frontend/package-lock.json` committed |
| `backend/contracts` | Frozen DTOs and Protocols. No Django, no ORM models. 45 exports |
| `backend/shared` | Port binding, 6 deterministic fakes, HTTP plumbing, scope resolver, fixtures |
| Profiles | `standalone`, `integrated`, `production`, plus a clearly-labelled local SQLite test profile |
| `M00` demo | Real migrations, real REST API, real React page. No business domain |
| `contracts/` | 7 common schemas, M00 OpenAPI generated from code, consumer fixtures, 14 packets |
| `contracts/manifest.json` | 11 frozen entries, each with a sha256 and an owner |
| `scripts/dev.py` | doctor, up, migrate, seed, check, evidence, down + integrated variants |
| `scripts/arch_check.py` | 7 static checks, each with a negative test proving it rejects |
| `scripts/contract_manifest.py` | Drift detection naming the file and both hashes |
| Frontend | Shell, API client, en/ml i18n, generated TS client, 38 tests |
| `infra/` | Both Dockerfiles; 5 images pinned by digest resolved from live registries |
| CI | 5 jobs: contracts, guards, backend-on-PostgreSQL, frontend, containers |

## Test numbers as last recorded

```
python   284 passed / 284    (local SQLite profile)
frontend  38 passed / 38
static   ruff check, ruff format, arch_check (7), manifest, eslint, tsc,
         vite build, makemigrations --check, spectacular --fail-on-warn  -- all clean
browser  NOT RUN (no container engine; recorded as not-run, not as passing)
```

## CI: green

Run [35419072164](https://github.com/Aravind-Unni/School-Managment-Software/actions/runs/35419072164)
on `e1f6704` — **all five jobs green**:

| job | result |
|---|---|
| contracts and architecture | success |
| guards reject real violations | success |
| backend suite on real PostgreSQL | success — **284 passed** |
| frontend | success |
| container images build | success |

**284 passed against PostgreSQL 17.11 — the same count as the local SQLite run**,
so no test is silently skipped on either backend. The PostgreSQL run is the
authoritative one.

## CI's first run — and the two defects it caught

Run [35418749812](https://github.com/Aravind-Unni/School-Managment-Software/actions/runs/35418749812):
**4 of 5 jobs green.** `contracts`, `guards`, `frontend` and `containers` passed.
`backend` failed — and it was right to.

**1. Resource namespace collision (critical).** `ResourceNames.stem` sanitised the
joined `developer_worktree_module` string and truncated it to 40 characters. CI's
checkout path is long, so the module id was chopped off the end and **M00, M04 and
M14 all resolved to the same Compose project and database.** That is a direct
violation of "two simultaneous module profiles have isolated resources". It passed
locally only because this machine's worktree name is short.

Fixed: the namespace is composed from individually-bounded components, so the
joined string is never truncated and both discriminators — the worktree hash and
the module id — always survive. `stem()` now raises rather than returning a name
that lost either, because refusing to start beats two stacks silently sharing one
database.

**2. `dev.py` assumed a `.venv` existed.** CI installs from the lockfiles into the
runner's Python, so `check --suite contracts` reported the contract tests as "not
run" and failed the build for the wrong reason. `test_interpreter()` now falls back
to the current interpreter when it can import pytest, and still returns an honest
"not run" when nothing can.

14 regression tests cover both, including 15 modules × 5 resource kinds × 5
developer/path shapes asserted mutually distinct.

Also now genuinely verified **in CI**: both Dockerfiles build from lockfiles, all
five images are digest-pinned, every module's generated Compose file parses, and
migrations apply to real PostgreSQL 17.11 with no model drift.

## What is NOT verified

**The container path was never executed.** There is no container engine on the
verification machine: `/usr/local/bin/docker` is a dangling symlink left by an
uninstalled Docker Desktop, and only the Homebrew `docker-compose` binary
survives — which cannot start anything without a daemon.

So these four remain unverified, and `acceptance.json` lists them as such rather
than claiming them:

- a fresh checkout booting the placeholder via `up`/`migrate`/`seed`
- the REST endpoint and React page inside the container stack
- browser tests producing results
- worker crash/retry behaviour

Resource isolation is **no longer** on that list: CI exposed a real collision in
it, the fix is tested across five developer/path shapes, and CI proves both images
build and every module's Compose file renders.
(CI end-to-end is now verified — see above. The remaining items below all need a
local container engine.)

`doctor` reports the missing engine and exits 2, which is the honest-failure
behaviour B00 asks for.

## Next session — concrete first action

1. `python3 scripts/dev.py doctor` — confirm a container engine is present.
   If not, install one; that is the single blocker for the remaining criteria.
2. Then, in order:
   ```bash
   python3 scripts/dev.py up      M00 --profile standalone
   python3 scripts/dev.py migrate M00 --profile standalone
   python3 scripts/dev.py seed    M00 --scenario baseline
   python3 scripts/dev.py check   M00 --suite standalone
   npx playwright install chromium --prefix frontend
   python3 scripts/dev.py check   M00 --suite browser
   python3 scripts/dev.py evidence M00
   ```
3. Prove isolation for real: run `up M00` in this worktree and a second module in
   another worktree simultaneously, and confirm distinct databases and ports.
4. Update `acceptance.json`: move each criterion from `unverified_criteria` to
   `verified_criteria` **only** after observing it.

**Do not start a business module until the foundation is peer-reviewed and
merged.** After merge, module work starts from `main`, and the first step for any
module is its contract packet — not code.

## Decisions worth knowing

- **TypeScript 5.9.3, not 7.0.2.** 7.x is the new native port and
  `typescript-eslint` caps support at `<6.1.0`; pinning "latest" would have
  broken type-aware linting immediately.
- **Node 22.22.2 for the frontend.** `vitest` 5 and `jsdom` 30 require ≥22;
  the host's default Node 20.19.5 cannot run them. The container pins 22.23.2.
- **`ATOMIC_REQUESTS = False`.** A hidden per-request transaction would make
  "audit and outbox join the caller's transaction" untestable.
- **`arch_check` derives its production exemption from the AST**, not a comment.
  The first attempt used a trailing `# arch-allow` marker; `ruff format` moved it
  to another line and silently broke the check.
- **Business module directories have no `__init__.py`**, but note precisely why
  that helps: the import still succeeds as a namespace package. The real
  guarantee is that `registration.py` is absent, plus an `arch_check` rule.
- **`M00` stays permanently.** It is the regression test for the foundation.
