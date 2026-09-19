# School-Managment-Software

An online English/Malayalam school web product for one Indian CBSE campus,
Standards 1–12, up to 4,000 students. The product is reused for other schools
through **separate deployments**, each with its own database and its own private
storage credentials.

**This repository currently contains the shared development foundation only
(B00).** None of the fourteen business modules is implemented. Read
[`docs/foundation/progress.md`](docs/foundation/progress.md) for exactly where
things stand and [`docs/foundation/handoff.md`](docs/foundation/handoff.md)
before starting work.

---

## First setup

You need **Python 3.12+**, **Node 22.22.2+**, and a **container engine** (Docker
Desktop, colima, or equivalent). Then:

```bash
# 1. Say what is missing before anything else. This works on a fresh checkout
#    with no virtual environment -- it is standard library only.
python3 scripts/dev.py doctor

# 2. Create the environment from the committed, hash-pinned lockfiles.
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install -r backend/requirements.txt \
                                -r backend/requirements-dev.txt
npm ci --prefix frontend

# 3. Confirm.
python3 scripts/dev.py doctor
```

`doctor` exits nonzero when a prerequisite is missing and names it. It prints a
**redacted** configuration view: secrets appear as `<set>`/`<unset>` and a
database URL keeps its host but loses its password.

There is nothing to copy into `.env`. `.env.example` documents variable **names
only**; `dev.py up` generates real local secrets into `dev/secrets/`, which is
outside Git.

## Starting a module

One module runs at a time, in its own isolated stack:

```bash
python3 scripts/dev.py up      M00 --profile standalone   # prints the real URLs
python3 scripts/dev.py migrate M00 --profile standalone
python3 scripts/dev.py seed    M00 --scenario baseline
```

`M00` is the **placeholder demo module**. It owns no school domain and exists to
prove the foundation works. The fourteen business modules are `M01`–`M14`; asking
for one that has no code yet fails with a clear message and exit status 3 rather
than booting an empty app.

| id | slug | id | slug |
|---|---|---|---|
| M01 | access | M08 | transport |
| M02 | registry | M09 | library |
| M03 | timetable | M10 | alumni |
| M04 | attendance | M11 | communications |
| M05 | assessment | M12 | files |
| M06 | performance | M13 | exchange |
| M07 | fees | M14 | platform |

Ports are allocated dynamically and every resource is namespaced by
`(developer, worktree, module)`, so **two developers, or one developer running
two modules, never collide.**

## Running checks

```bash
python3 scripts/dev.py check M00 --suite contracts    # no containers needed
python3 scripts/dev.py check M00 --suite standalone   # needs a running stack
python3 scripts/dev.py check M00 --suite browser      # needs a stack + browser
python3 scripts/dev.py evidence M00                   # collect into one bundle
```

Every suite writes a machine-readable report to `dev/evidence/<namespace>/`.

**A suite that cannot run is recorded as `not-run`, never as passing.** That is
deliberate: `evidence` exits nonzero unless every suite actually passed, so a
missing browser or a stopped database cannot be mistaken for a green build.

Directly, without the CLI:

```bash
.venv/bin/python -m pytest tests -q      # local SQLite profile (see caveat below)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
python3 scripts/arch_check.py            # forbidden imports, fakes in production
python3 scripts/contract_manifest.py --check   # contract schema drift
npm run --prefix frontend lint && npm run --prefix frontend typecheck
```

> **Caveat:** a bare `pytest` uses `config.settings.test_sqlite`, a local-only
> profile. It cannot prove PostgreSQL behaviour, migrations against PostgreSQL,
> worker/broker behaviour, or resource isolation. CI and
> `dev.py check --suite standalone` run against real PostgreSQL, and those are
> authoritative.

## Stopping work

```bash
python3 scripts/dev.py down M00
```

`down` stops containers and **never deletes a volume**, so seeded data survives.
It prints the exact `docker volume rm` command if you do want the data gone.

## Resuming work

1. `docs/foundation/progress.md` — where things stand and the next action.
2. `docs/foundation/handoff.md` — what is verified, what is **not**, and the
   known gaps.
3. `docs/modules/<ID>/README.md` and `contracts/<ID>/PACKET.md` for your module.
4. `python3 scripts/dev.py doctor`.

**Never regenerate the foundation for a feature request.** See
[`AGENTS.md`](AGENTS.md).

## Layout

```
backend/config      Django settings per profile: standalone, integrated, production
backend/contracts   Immutable shared DTOs and Protocols. No Django. No ORM models.
backend/shared      Harness: port binding, fakes, HTTP plumbing, fixtures
backend/modules/<slug>   One business module each. Never imports another module.
frontend/src/app         Shell: routing, language, module registry
frontend/src/shared      API client, error envelope, i18n
frontend/src/features/<slug>   One feature each, with its own nav metadata
contracts/<ID>      Per-module OpenAPI, JSON Schema, fixtures + manifest.json
dev/harness         Runner support: naming, ports, secrets, Compose rendering
dev/modules/<ID>    Which containers a module declares
tests/contracts     Frozen-interface assertions
tests/integration   API, authorisation matrix, transaction trail, CLI
scripts             dev.py, arch_check.py, contract_manifest.py
infra               Dockerfiles and digest-pinned image record
```

## Rules that are enforced, not merely documented

- **Identity is server-derived.** A request carrying `X-School-Id`, `X-Role` or
  similar is **rejected**, not ignored.
- **Cross-school access returns 404, never 403**, so probing cannot distinguish
  "not yours" from "does not exist".
- **Deny by default.** An action with no policy rule is denied.
- Audit and outbox rows are written **in the caller's transaction**; a rollback
  removes them.
- `expected_version` is required on updates; a mismatch is **409**.
- Money is integer **INR paise**; marks cross the wire as **decimal strings**.
- Instants are **UTC**; civil dates are **Asia/Kolkata**.
- Production **refuses** fake adapters, development personas and demo fixtures.
- No module may import another module.

## Out of scope

No runtime AI, no online exams, no GPS, no payroll, no full accounting. The
entire approved scope is released together. Kubernetes is **not** required.
