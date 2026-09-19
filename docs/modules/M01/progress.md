# M01 access — progress

## Original request

Implement **M01 Identity, permissions and two-factor authentication** as an
independently runnable profile inside the shared school repository: school-scoped
accounts, configurable roles, relationship-aware authorization, secure sessions
and a complete 2FA lifecycle. Real backend, frontend, database and migrations;
deterministic test doubles for external business modules. Inspect contracts first,
propose missing schemas, then implement and test. Do not integrate other business
modules or invent school policy.

## Source and contract identity

| | |
|---|---|
| Branch | `m01/access-identity` |
| Started from | `1b01e7312e4bf4d0030c0623799863808d112ec2` (`main`, B00 merged) |
| Manifest revision at start | `school-contracts-v3-draft`, M01 `status: not_started`, zero artefacts |
| Manifest revision now | `school-contracts-v3-draft` (unchanged); M01 fixtures recorded, **not frozen** |
| PR | to be opened as a draft |

## Prerequisite state

B00 is merged and its CI is green, **but B00 was never marked
STANDALONE_VERIFIED**: four of its criteria are unverified because no container
engine exists on this machine. That directly limits M01 — see Blockers.

## Six contract conflicts found and reconciled

M01's specified interfaces conflicted with contracts B00 froze and merged. All six
were verified against running code before anything changed, and every change is
**additive** — B00's suite passes unchanged and the demo registration needed no
edit.

| # | Conflict | Reconciliation |
|---|---|---|
| 1 | `authorize()->Decision` vs frozen `check()->None` | Added `authorize` + `require_recent_2fa`; `check`/`is_allowed` now derive from `authorize` so they cannot disagree |
| 2 | All 5 M01 permission codes rejected (2-segment, slug-prefixed rule) | Codes may be multi-segment; ownership declared as **prefixes**; slug prefix is the default so existing registrations are untouched |
| 3 | `/api/v1/...` vs `/api/<slug>/` one-include-per-module | Added `api_path_roots` + `assert_no_registration_collisions`; two modules cannot claim one root or one permission prefix |
| 4 | `RelationshipFacts` fields differed 4 each way | Extended additively with `school_id`, `section_ids`, `subject_ids`, `valid_until`, plus `is_active_on()` |
| 5 | Envelope `schema_version`+`correlation_id` vs `envelope_version` | Both keys emitted for one revision; v4 retires `envelope_version` |
| 6 | Registry needs 4 methods, port had 1 | Extended `RegistryPort`; shared fake implements all four |

`PlatformPort` was **not** changed: M01's signatures will come from a facade inside
the module, leaving B00's DTO contract intact.

Also added `ErrorCode.RATE_LIMITED -> 429` with a finite `Retry-After`. B00's
invariant is that the code determines the status, so returning 429 under a 422 code
was not possible.

## Completed behaviour (steps 1-4)

- **Contract artefacts, authored before coding**: `openapi-seed.yaml` (15
  operations), `schemas/dtos.schema.json` (14 DTOs, every write shape
  `additionalProperties: false`), `error-codes.json` (20 rows), fixtures (5
  accounts, 4 roles, preloaded expired challenge / used recovery code / pending
  case, 18 acceptance outcomes).
- **All owned records** as Django models, with invariants in *database*
  constraints: one holder per grant, scope_id present iff the scope needs it, at
  most one active factor per account, at most one pending case per account.
- **Closed permission catalogue** as data. Step-up is a property of the action.
  No hard-coded privileged username — ownership is a role flag.
- **Pure authorisation policy** (`services/policy.py`): no DB, no clock, no
  Django. Tenant check first, deny by default, inclusive validity windows,
  section/subject/self scope matching, and **no role rank**.
- **Real Access service** (`services/authorize.py`): reads only M01's tables,
  never calls Registry, caches nothing.
- **Crypto**: Fernet-encrypted seeds with the key outside the database, salted
  recovery-code hashes, hashed session tokens. Missing or rotated key fails loudly.
- **TOTP**: pyotp, six digits / 30s / ±1 step, replay blocked by a conditional
  UPDATE on `last_accepted_step` whose row count is checked.
- **Module-aware profiles**: `MODULE_ID` selects the app; **M01 gets no synthetic
  persona** in any profile, because a persona would bypass the login flow.

- **Step 1 — accounts and sessions**: all 11 tables migrated, login with a
  pre-authentication challenge, session creation and rotation, CSRF double-submit,
  Secure/HttpOnly/SameSite cookies, throttling by account and address with a
  progressive but always FINITE cooldown.
- **Step 2 — TOTP and recovery**: enrolment (including the first-enrolment path for
  an account that cannot sign in without a factor), activation returning ten
  one-time recovery codes, replay-proof verification, recovery-code sign-in,
  lost-device cases approved by a different person.
- **Step 3 — permissions and delegation**: closed catalogue, pure policy, real
  Access service, escalation/cycle/last-owner protection, optimistic concurrency,
  `RoleGrantsChanged.v1` and `FactorReset.v1`.
- **Step 4 — frontend**: seven screens, 49 message keys in English and Malayalam,
  generated TypeScript client, seven Playwright journeys.
- 15 REST endpoints; generated `openapi.yaml` asserted to match the pre-written seed
  in both directions.

## Test results as last recorded

```
M01 suite      53 passed, 1 skipped   (SQLite profile; the skip needs PostgreSQL)
B00 foundation 294 passed             (unchanged by M01)
frontend        47 passed
static         ruff, arch_check, manifest, eslint, tsc, vite build,
               django check, makemigrations --check, spectacular --fail-on-warn
browser        NOT PASSED -- blocker, see below
```

## CI run 35451437482

| job | result |
|---|---|
| contracts and architecture | success |
| guards reject real violations | success |
| backend suite on real PostgreSQL | success |
| frontend | success |
| container images build | success |
| **M01 access suite on real PostgreSQL** | **success — 158 passed, 1 skipped** |
| M01 browser suite against a real stack | **failure** (ordering bug, fixed) |

Migrations verified on an **empty** database and then on **populated** data. Two
defects the run exposed, both fixed: the browser job ran `doctor` before installing
dependencies, and the `requires_postgres` race test called `pytest.skip()`
unconditionally so it could never run in any environment.

## Incomplete behaviour

- The **browser suite has never executed** (no container engine). A CI
  `m01-browser` job brings up the real stack via Compose and runs it; it has not run.
- `up`/`migrate`/`seed` against real containers never executed here.
- No account-creation or deactivation endpoint yet: `/accounts` is read-only, which
  is all the acceptance tests need. `accounts.manage` covers the write path when it
  is added.
- Factor **replacement** from an existing session is implemented in the service
  (`disable_factor`, then enrol) but has no REST endpoint or screen yet.

## Exact next step

1. Get the shared contract changes reviewed — see `handoff.md` §4. Everything else
   waits on that, because a later revision ripples into every module built meanwhile.
2. Install a container engine, then:
   ```bash
   python3 scripts/dev.py up M01 --profile standalone
   python3 scripts/dev.py migrate M01 --profile standalone
   python3 scripts/dev.py seed M01 --scenario baseline
   python3 scripts/dev.py check M01 --suite standalone
   python3 scripts/dev.py check M01 --suite browser
   python3 scripts/dev.py evidence M01
   ```
3. Move each item from `acceptance.json` → `blockers` only after observing it.

## Blockers

1. **No container engine.** `up`/`migrate`/`seed` and the browser suite cannot run
   here (`/usr/local/bin/docker` is a dangling symlink from an uninstalled Docker
   Desktop). A CI `m01-browser` job was built as the agreed mitigation but has not
   executed. Until it passes, the browser suite is a **required check that has not
   passed**, which M01 defines as a blocker.
2. **No second developer has verified from a fresh checkout** — required by the
   whole-module gate.
3. **The shared contract changes are unreviewed.** They affect every future module.

**`STANDALONE_VERIFIED` is therefore NOT recorded.** Completed steps do not imply
it.

## Pending integration tests (never run against real modules)

- Recheck real Registry relationships (currently a deterministic fake).
- File download revocation after a role change (M12 does not exist).

These are **PENDING**, not passing. Independent approval does not imply they hold.
