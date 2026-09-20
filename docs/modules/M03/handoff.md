# M03 handoff

## Read first

The contract gate is **closed**: the packet was approved as proposed and frozen
under revision `school-contracts-v4` on 2026-09-20 by Abhinav M. **No module code
exists yet** — tests come next, written from the frozen contract.
`STANDALONE_VERIFIED` is false and cannot be otherwise until the whole module is
built and a second developer verifies it from a fresh checkout.

Read, in order:

1. [progress.md](progress.md) — where things stand and the exact next step.
2. [`contracts/M03/review-decisions.md`](../../../contracts/M03/review-decisions.md)
   — the review outcome, and the four validations this module cannot perform.
3. [`contracts/M03/PACKET.md`](../../../contracts/M03/PACKET.md) and
   [`ports.md`](../../../contracts/M03/ports.md).

Session source: branch `m03/timetable-calendar`, branched from `main`
`aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a`, manifest revision `school-contracts-v4`.

## What is available today

A reviewable contract, and nothing else:

| Artefact | State |
|---|---|
| `contracts/M03/openapi.json` | 21 operations, 16 paths — frozen |
| `contracts/M03/schemas/dtos.schema.json` | 35 closed definitions — frozen |
| `contracts/M03/schemas/events.schema.json` | 2 payloads — frozen |
| `contracts/M03/error-codes.json` | 33 rows, 7 conflict codes — frozen |
| `contracts/M03/ports.md` | provided and consumed ports — reviewed |
| `contracts/M03/fixtures/*` | baseline scenario, 12 validated examples, 22 acceptance cases — frozen |
| `contracts/manifest.json` | all seven files frozen; **27 frozen entries** where 20 were before |

Not available: any Django app, migration, endpoint, React route, seed, or test.
`backend/modules/timetable/` has no `registration.py`, so `dev.py up M03` refuses to
start rather than serving an empty app, and `arch_check.py` rejects any import of it.

## Startup commands

These are the commands the module must support once it exists. **None of them has
been run for M03, because there is nothing to run.** Use the `up` output for real
URLs; ports are allocated dynamically and are never fixed.

```bash
python3 scripts/dev.py doctor
python3 scripts/dev.py up M03 --profile standalone
python3 scripts/dev.py migrate M03 --profile standalone
python3 scripts/dev.py seed M03 --scenario baseline
python3 scripts/dev.py check M03 --suite standalone
python3 scripts/dev.py check M03 --suite contracts
python3 scripts/dev.py check M03 --suite browser
python3 scripts/dev.py evidence M03
python3 scripts/dev.py down M03
```

## Printed URLs

None. There is no stack to start. `dev.py up` prints the allocated API and frontend
URLs; do not assume a port.

## Fictional login instructions

Not implemented. When it is: the standalone profile derives a **fixed synthetic
persona server-side**, on loopback only, defaulting to T1 (class teacher of C1). The
browser cannot select or change it, and any client-asserted identity header is a
hard 400. Real login, sessions and 2FA are M01's and stay **explicitly pending**.

## Migrations

None yet. When they exist they must apply to both an empty database and a seeded
one, and any irreversible migration must be documented here with its reason.

## Commands actually run this session, and their results

| Command | Result |
|---|---|
| `git rev-parse` / `git log` / `git branch` | source identity read from the checkout, recorded above |
| `python3 scripts/dev.py doctor` | **exit 2** — no container engine (dangling Docker symlinks only). Node v20.19.5 is below the `^22.22.2 \|\| >=24` the frontend requires |
| `python3 scripts/dev.py check M00 --suite contracts` | **passed** — manifest current at `school-contracts-v4` (20 frozen), 7 architecture checks, 105 shared contract tests |
| `python3 scripts/contract_manifest.py --check` | failed as expected on the seven new unhashed files, then passed after `--update` |
| jsonschema validation of `fixtures/responses.json` | **12 examples and 2 events valid**, 0 failures, against the proposed schemas and the frozen event envelope |

Nothing else was executed. No standalone suite, no browser suite, no migration, no
seed — because none exists and no container engine is present.

## Pending integration tests

These are **PENDING**, not passing. Independent approval of M03 would not imply any
of them. Replace the fakes and run them in Section C.

1. **Real attendance authorisation for a dated substitution.** M03 can prove it
   publishes the trusted fact and that the fact expires. It cannot prove M04 honours
   it; M04 does not exist.
2. **Real authentication and 2FA.** The stale-2FA path on publish is exercised
   against the fake Access adapter only.
3. **Real Registry provider.** Section, subject, staff and academic-year existence
   are unvalidated, because the frozen `RegistryPort` exposes no lookup for them.
   See `contracts/M03/ports.md`, gaps 1-4.

## Blockers for whoever picks this up

1. No container engine here → standalone and browser suites cannot run.
2. Node v20 here → frontend typecheck, unit tests and production build cannot run.
3. B00's acceptance gate is still open, and is not closeable from this module.
4. Four Registry lookups do not exist, so four validations are not performed. See
   `contracts/M03/ports.md`, gaps 1-4.
