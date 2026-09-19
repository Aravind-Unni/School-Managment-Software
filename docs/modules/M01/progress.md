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
| PR | not yet opened |

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

## Completed behaviour

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

## Incomplete behaviour

Not yet written: login/challenge, session, enrolment, recovery and role services;
the platform facade; throttling; migrations; the 15 REST endpoints; seed scenario;
`tests/modules/M01/`; the React feature with English/Malayalam screens; the
Playwright specs; the CI Compose+Playwright job; `handoff.md`; `acceptance.json`;
generated `openapi.yaml` diffed against the seed.

## Exact next step

Write `services/login.py` (pre-auth challenge, throttling, session creation with
rotation) and `services/sessions.py`, then `migrations/0001_initial.py`, then
verify the atomic TOTP replay and the concurrent recovery-code race against a real
database.

## Blockers

1. **No container engine.** `up`/`migrate`/`seed` and the browser suite cannot run
   on this machine (`/usr/local/bin/docker` is a dangling symlink from an
   uninstalled Docker Desktop). Mitigation agreed: a CI Compose+Playwright job.
   Until it runs, the browser suite is a **required check that has not passed**, so
   M01 cannot be marked STANDALONE_VERIFIED.
2. **Second developer verification from a fresh checkout has not happened** — also
   required for STANDALONE_VERIFIED.

## Pending integration tests (never run against real modules)

- Recheck real Registry relationships (currently a deterministic fake).
- File download revocation after a role change (M12 does not exist).

These are **PENDING**, not passing. Independent approval does not imply they hold.
