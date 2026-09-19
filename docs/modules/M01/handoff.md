# M01 access — handoff

Read this before touching M01 or anything it changed. **M01 is NOT
`STANDALONE_VERIFIED`** — see Blockers.

## 1. What you can rely on

Verified against a real database (SQLite locally, PostgreSQL in CI) by 53 tests.

| Guarantee | Where |
|---|---|
| A correct password yields a CHALLENGE, not a session; no business endpoint accepts it | `services/login.py` |
| An unknown login and a wrong password are indistinguishable, and cost the same hash work | `begin_login` compares against a dummy hash |
| A TOTP code cannot be replayed, even inside its own 30-second step | conditional UPDATE on `last_accepted_step`, row count checked |
| Five wrong codes invalidate the CHALLENGE, never the account | `record_failed_attempt` in its own transaction |
| A recovery code is single-use; concurrent reuse has exactly one winner | conditional UPDATE on `used_at IS NULL` |
| Recovery revokes the old factor and every session; the session is RECOVERY level and satisfies no business permission | `recover_with_code` |
| Factor reset is approved by a DIFFERENT person, revokes everything, emits `FactorReset.v1` | `approve_reset_case` |
| Cross-school access is 404, never 403 | tenant check runs first in `services/policy.py` |
| Deny by default; no role rank | closed catalogue + `evaluate` |
| No self-escalation; delegation bounded by the delegator's own scope | `assert_no_escalation` |
| Last active owner cannot be removed | `assert_owner_survives` |
| `expected_version` required; missing is 422, stale is 409 | `replace_grants` |
| Unknown write fields are 422 naming the field | `StrictSerializer` |
| Seeds encrypted with a key outside the database; codes and tokens hashed | `services/crypto.py` |
| No password, OTP, seed or recovery code in any audit row or event | `platform_facade.redact`, tested nested/in-list/case-insensitive |
| A client-asserted `X-School-Id` is REJECTED, not ignored | shared middleware, guards run first |
| CSRF double-submit on every cookie-authenticated write | `middleware.py` |
| Device-loss recovery works with **no SMS service** | `notifications` is not even a declared consumer |

## 2. What is NOT verified — do not claim these

1. **The browser suite has never run.** No container engine on this machine. M01's
   own rule is that a required skipped check is a **blocker**, so this is one. A CI
   job (`m01-browser`) brings up the real stack via Compose and runs the seven
   journeys; it has not executed.
2. **`up` / `migrate` / `seed` against real containers** — written, never run here.
3. **A real two-thread recovery-code race** — marked `requires_postgres` and
   SKIPPED on SQLite. A green tick there would be a false claim about concurrency.
4. **A second developer from a fresh checkout** — required by the whole-module gate.

## 3. Pending integration — NOT passing

- **Real Registry relationships.** M01 runs against a deterministic fake. Re-run in
  Section C against M02.
- **File download revocation after a role change.** M12 does not exist, so the
  acceptance case "role removal affects evidence downloads" is **not covered**. API
  and service paths are covered; the private-file path is unexercised.
- **Real 2FA for other modules.** Every other module still binds fake Access with a
  synthetic persona. Wiring them to M01's real Access is Section C.
- Worker crash/retry is **not applicable**: M01 declares no jobs, so no broker or
  worker starts and nothing is claimed.

## 4. Shared contracts M01 changed — THESE NEED REVIEW

M01's specified interfaces conflicted with contracts B00 froze and merged. Every
change is additive and B00's 294 tests pass unchanged, but they touch files outside
M01's allowed paths and affect **every future module**. Full list in
`acceptance.json` → `reviewed_interfaces_changed`. The headline items:

- `AccessPort` gained `authorize()`/`require_recent_2fa()`; `check()` now derives.
- Permission ownership is declared as **prefixes**, not the slug.
- `/api/v1/` with declared `api_path_roots` and collision detection.
- `RegistryPort` gained four methods; the shared fake implements them.
- `ErrorCode.RATE_LIMITED → 429`.
- A module may contribute middleware and declare public paths.

**`PlatformPort` was deliberately NOT changed** — M01 uses an internal facade, so
B00's DTO contract and the harness test adapter are untouched.

## 5. Traps

- **Do not increment a counter inside a transaction you are about to roll back.**
  The attempt counter did exactly that, so a challenge was never invalidated and an
  attacker had unlimited guesses. Failure bookkeeping needs its own transaction.
- **A TOTP code cannot be reused immediately after enrolment** — enrolment consumed
  that time step. Tests must advance the clock ~31s. This is correct behaviour.
- **Do not delete used recovery codes.** Keeping them preserves the record of which
  was spent and makes a replay a correct 409 rather than a confusing 422.
- **Authorisation is checked BEFORE step-up.** An actor missing both gets 403, not a
  step-up prompt — prompting would reveal the action exists and they nearly have it.
- **A recovery session must never satisfy a two-factor requirement.** It maps to
  `AuthLevel.PASSWORD` on purpose.
- **`settings` is not process state.** Anything stashed on it disappears when an
  `override_settings` block pops. Use `shared.ports.runtime`.
- **`MODULE_ID` selects the profile AND test collection.** `pytest` alone runs the
  M00 suite; M01's needs `MODULE_ID=M01` and its own path.

## 6. Open questions for the humans

1. **Approve or revise the shared contract changes in §4.** Everything else waits on
   this: a later revision would ripple into every module built meanwhile.
2. **Is the proposed 2FA minimum accepted?** Mandatory for owner/administrator/staff;
   parent and student enforcement is school-configurable and ships **OFF**. A fixture
   exercises the configurable path; it does not activate a production policy.
3. **Is the five-minute step-up window right for this school?** It is the proposed
   profile, applied to every action the catalogue marks sensitive.
4. **Owner recovery process.** Implemented as a case approved by another authorised
   person, with no requirement that a second owner exists. The company-controlled
   verified process it should defer to is not specified anywhere.
5. **429 in the shared taxonomy.** B00 froze 401/403/404/409/422; throttling needs a
   retry signal, so `rate_limited` was added. Confirm.
6. **Session lifetime.** Currently 12 hours with no "remember me", chosen because a
   school device is often shared. Confirm.
