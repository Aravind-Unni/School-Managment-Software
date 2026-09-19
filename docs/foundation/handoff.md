# Foundation handoff — B00

Read this before touching anything. It tells you what you can rely on, what you
cannot, and where the traps are.

**The foundation is built once. Do not regenerate it for a feature request.** See
[`../../AGENTS.md`](../../AGENTS.md).

---

## 1. What you can rely on

These are tested and other modules will depend on their exact behaviour. Changing
any of them is a **contract revision** requiring review, not a local edit.

| Guarantee | Where it lives | Proven by |
|---|---|---|
| Error envelope `{code,message_key,field_errors,request_id}` mapped to 401/403/404/409/422 | `contracts/errors.py` | `tests/contracts/test_error_envelope.py` |
| Identity is server-derived; a client-asserted header is **rejected** | `shared/http/context.py`, `middleware.py` | `test_demo_api.py` (6 headers) |
| Cross-school access is **404, not 403** | `shared/fakes/access.py`, checked before permission | `test_authorization_matrix.py` |
| Deny by default; unknown action denied | `shared/fakes/access.py` | `test_authorization_matrix.py` |
| Access never calls Registry recursively | `ScopeFacts` / separate `RelationshipFacts` | `test_scope_and_values.py` |
| Audit + outbox join the caller's transaction | `fakes/platform.py` opens no transaction | rollback test in `test_transaction_trail.py` |
| `expected_version` mismatch is 409 with both versions | `modules/demo/services.py` | `test_transaction_trail.py`, `test_demo_api.py` |
| `items`/`next_cursor`, opaque cursors, capped page size, malformed cursor is 422 | `contracts/pagination.py`, `shared/http/pagination.py` | `test_pagination_contract.py`, `test_demo_api.py` |
| Integer INR paise; decimal-string marks; UTC instants; Asia/Kolkata dates | `contracts/values.py` | `test_scope_and_values.py` |
| `ResourceGrant` never accepted from a browser, at any nesting depth | `shared/http/guards.py` | `test_demo_api.py` |
| Production refuses fakes, personas, demo fixtures | `PortRegistry`, `production.py`, `arch_check.py` | `test_production_safety.py` + CI guards job |
| No module imports another module | `scripts/arch_check.py` | `test_arch_check.py` (injects a violation) |
| Async behaviour is never faked | `TestPlatformAdapter.enqueue` raises | `test_transaction_trail.py` |

## 2. What is NOT verified — do not claim these

**No container engine existed on the verification machine.**
`/usr/local/bin/docker` is a dangling symlink from an uninstalled Docker Desktop;
only the Homebrew `docker-compose` binary remains, and compose cannot start
anything without a daemon. `doctor` reports this and exits 2.

Consequently these are **written but never executed**:

1. `up` / `migrate` / `seed` against real containers
2. the REST endpoint and React page inside the container stack
3. Playwright browser tests (recorded `not-run`, never `passed`)
4. worker crash/retry against a real broker
5. two simultaneous stacks genuinely running at once
6. the CI workflow — it runs on first push

`acceptance.json` lists each with its blocker and how to verify it. **If you
verify one, move it and say who observed it.** If you cannot, leave it.

> A bare `pytest` uses `config.settings.test_sqlite`. It **cannot** prove
> PostgreSQL behaviour, PostgreSQL migrations, broker behaviour or isolation. The
> CI `backend` job is authoritative.

## 3. Explicitly pending

**Real authentication and 2FA are not implemented.** Every module except `M01`
runs against `FakeAccess` and a fixed synthetic persona derived server-side on
loopback only. `FakeAccess` is *not* `allow_all`: it evaluates a policy table,
denies by default, and simulates stale 2FA on purpose, so a module developed
against it still handles 401 on writes.

When `M01` lands, the persona branch is disabled by configuration and real
session-derived contexts flow through unchanged — `RequestContext` is the same
type either way. **Your module needs no change for this**, which is the point.

## 4. Traps

- **`ruff format` will move a trailing comment.** `arch_check` originally relied
  on a `# arch-allow` comment sitting on the flagged line; the formatter moved it
  and the check silently stopped firing. It now derives the exemption from the
  AST. Do not reintroduce a line-position-dependent rule.
- **`--json-report-file` alone writes nothing.** pytest-json-report needs
  `--json-report` too. Without it the suite goes green and no machine-readable
  report exists. Both `dev.py` and CI pass both flags; a regression test guards it.
- **A directory without `__init__.py` is still importable** as a namespace
  package. `import modules.attendance` succeeds and yields an empty module. The
  guarantee is the absence of `registration.py` plus an `arch_check` rule — not
  the missing `__init__.py`.
- **Do not set `ATOMIC_REQUESTS = True`.** It would make the rollback assertion
  meaningless.
- **Do not add `task_always_eager`.** Eager execution cannot demonstrate crash or
  retry, and claiming it did is forbidden.
- **A collection has no single subject**, so a relationship-gated rule denies
  every list call. `M00` learned this the hard way: listing is school-scoped,
  reads are relationship-gated. Expect the same split in your module.
- **Frozen dataclasses still share mutable members.** `EventEnvelope` originally
  aliased the caller's payload dict. Copy into a read-only mapping.
- **zsh does not word-split unquoted variables.** A `for x in $LIST` loop in a
  setup script creates one directory with spaces in its name.

## 5. Starting a business module

1. Read `docs/modules/<ID>/README.md` and `contracts/<ID>/PACKET.md`.
2. **Contract first.** Produce the exact OpenAPI, JSON Schema, Protocol
   signatures, error enums and example fixtures. Get them reviewed. Freeze them in
   `contracts/manifest.json`. **Human gate — stop here.**
3. Only then write tests, then code.
4. Declare the module: `backend/modules/<slug>/registration.py` and
   `dev/modules/<ID>/module.json`. Declare **only** the resources you need — a
   module with no async work must not start a broker.
5. Add `<ID>` to `integrated.APPROVED_MODULE_IDS` when it is approved.
6. Write authorisation tests using the fixture cast: G1 guards S1+S2, G2 is
   unrelated to S1, T1 teaches C1, T2 is unassigned. **Include the deny rows.**

## 6. Open questions for the humans

1. **Is `school-contracts-v3-draft` the intended starting revision?** B00 said to
   start there and replace it with the actual approved revision. Nothing has
   replaced it yet.
2. **Which module is first?** `M01 access` and `M02 registry` are the obvious
   candidates since everything else consumes them, and `M01` is the one module
   that uses real login with only a fake Registry. `migration_dependencies` are
   empty everywhere until someone decides the order.
3. **Frontend data-fetching library?** The foundation ships none deliberately. The
   placeholder fetches in an effect and flags the lint rule inline rather than
   hiding it. The first real module should choose.
4. **Where does CI run, and is a container engine available there?** The workflow
   assumes GitHub-hosted runners with Docker. If CI moves, the `containers` job
   needs revisiting.
5. **Who owns each contract?** `manifest.json` records owners as
   `"<ID> <slug>"` placeholders. Real names or teams should replace them before
   the first module freeze, since the owner is who must review a revision.

None of these blocks reviewing the foundation. All of them block the first module.

## 7. One environmental note

A `CLAUDE.md` exists in the **parent directory** of this checkout
(`~/Downloads/CLAUDE.md`, i.e. one level above the repository). It describes an
unrelated product — a component risk-analysis / bill-of-materials platform — with
its own subsystem ids `S1`–`S11`, a five-stage story loop with human gates before
any code, a `make verify` target, and `docs/PROGRESS.md` / `DECISIONS.md` /
`BLOCKED.md`. None of those files or targets exist here, and its `S`-prefixed
subsystem ids directly conflict with this product's `M01`–`M14`.

Because it sits above the repository root, tooling may pick it up as project
instructions for work done in this directory. It was confirmed as **not
applicable** to this repository and was ignored for B00. If a future session sees
guidance about bills of materials, equivalence rules or ingester fleets, that is
the file — it is not about this product.

Its genuinely universal rules were honoured regardless, and are worth keeping:
never weaken a test to make it pass, never invent a domain fact, never report a
result you did not observe.
