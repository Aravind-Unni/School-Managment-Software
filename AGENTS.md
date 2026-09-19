# AGENTS.md — instructions for coding sessions in this repository

Read this file first, then
[`docs/foundation/progress.md`](docs/foundation/progress.md), then the packet for
the module you are working on.

---

## The rule that matters most

**The foundation is built once. Never regenerate it for a feature request.**

If you are asked to "add attendance" or "build the fees page", you are working on
**one module**. You are not rebuilding `backend/contracts`, `backend/shared`,
`scripts/dev.py`, the profiles, the fakes, or CI. Those exist, they are tested,
and other modules depend on their exact behaviour.

Signs you are about to make this mistake:

| Thought | Reality |
|---|---|
| "I'll set up the project structure first" | It exists. Read the layout in `README.md`. |
| "There's no test harness, I'll add one" | `tests/conftest.py` has the fixtures and fakes. |
| "I need a way to run this" | `python3 scripts/dev.py up <ID>`. |
| "I'll add a settings file" | Four profiles exist in `backend/config/settings/`. |
| "The error format isn't defined" | It is frozen. `contracts/common/error-envelope.schema.json`. |
| "I'll write a fake for Access" | `shared/fakes/FakeAccess` exists and denies by default. |
| "A new chat means a new project" | It does not. Read `progress.md`. |

A change to anything shared is a **contract revision**: it needs review and a new
`contracts/manifest.json` revision, not a local edit.

## Before writing any module code

1. Read `docs/foundation/progress.md` — current state and the next action.
2. Read `docs/modules/<ID>/README.md` and `contracts/<ID>/PACKET.md`.
3. Confirm the module's contract is **frozen in `contracts/manifest.json`**. If
   its status is `not_started`, the contract comes first: produce the exact
   OpenAPI, JSON Schema, Protocol signatures, error enums and example fixtures,
   get them reviewed, freeze them. **Then** implement.
4. `python3 scripts/dev.py doctor`.

## Session start

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py check M00 --suite contracts
```

If the contracts suite is red at session start, **fixing that is the session's
work.** Do not build on a broken foundation.

## Git

- Never switch branches over uncommitted work, and never overwrite it.
- New task: branch from the latest reviewed `main`.
- Unfinished task: **resume its existing branch**; do not start a parallel one.
- Merged task: branch fresh from `main`.
- Never leave `main` red. Never merge or deploy automatically.
- Read the actual starting commit and manifest revision yourself. Do not ask a
  human to supply values you can read with `git rev-parse` and `cat`.

## Things you must not do

- **Do not modify a test to make it pass.** Write up the problem and stop.
- **Do not weaken a guard.** Not `arch_check.py`, not the production refusals, not
  the deny-by-default policy. If a guard is wrong, that is a reviewed change with
  a reason, not a silent edit.
- **Do not invent a domain fact.** Not a CBSE rule, not a grading scale, not a fee
  structure, not a timetable convention. Ask.
- **Do not fabricate a dataset.** Synthetic fixtures for adversarial and
  structural tests are fine and expected. Inventing plausible-looking real school
  data is not.
- **Do not claim a result you did not observe.** If the browser suite did not run,
  it did not pass. `dev.py` records `not-run` for exactly this reason; do not
  paper over it in a summary.
- **Do not use eager Celery execution to claim worker crash or retry coverage.**
  `TestPlatformAdapter.enqueue` raises instead, on purpose.
- **Do not import another module.** Use a service port from `contracts/ports.py`.
- **Do not trust a client-supplied school, role or relationship.** Ever.
- **Do not widen the task** to route around a problem. Record the blocker.

## Stop and ask

Stop at these. Do not proceed because it seems obvious:

- any module SPEC or contract packet, before tests are written
- enabling any authorisation or equivalence rule
- any change to a shared interface in `backend/contracts`
- any accuracy threshold or tenancy/access-control change
- supplying corporate BOM-style real data or cross-manufacturer cases
  (request-only; not applicable to this product but the rule stands for any
  real-world dataset)
- every phase exit gate
- the first customer-facing report for each design partner

**Asking is not failure.** A well-formed request that names what you need, the
minimum that unblocks you, an acceptable partial and a suggested route to get it
is worth more than a workaround. Working around missing information is how this
project fails silently.

## When you finish

```bash
python3 scripts/dev.py check <ID> --suite contracts
python3 scripts/dev.py check <ID> --suite standalone
python3 scripts/dev.py evidence <ID>
```

Then rewrite `docs/foundation/progress.md` (or your module's progress file)
completely: current phase, status, branch name, the real test numbers, and the
concrete first action for the next session. Add open questions to the handoff.

**If context runs low, stop early and do this properly.** An orderly stop at 70%
beats an abrupt stop at 95%.

## Code conventions

- Modules under ~500 lines; `arch_check.py` enforces the ceiling.
- Decision logic pure: no IO, no clock, no globals. Time arrives as a
  `ClockPort`.
- Rules, schemas and thresholds are **data**, not code branches.
- No metaprogramming, no dynamic dispatch on strings, no inheritance past one
  level.
- Long names. Repetition over abstraction below three call sites.
- A docstring on every function: what it does, what it assumes, and what it does
  **not** handle.
- Write for an agent reading it cold in six months.
