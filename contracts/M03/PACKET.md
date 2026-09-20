# Contract packet — M03 central timetable and calendar

Status: **PROPOSED, NOT FROZEN.** `contracts/manifest.json` still records M03 as
`not_started`, and nothing in this directory is hashed. Read
[`review-decisions.md`](review-decisions.md) first: it lists fourteen decisions a
reviewer must make, and four things this module cannot validate because the frozen
Registry port does not expose them.

Owner: Developer A. Produced on branch `m03/timetable-calendar`, from `main`
`aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a`, manifest revision `school-contracts-v4`
(status `reviewed`, 20 frozen entries).

This replaces the placeholder packet with a reviewable proposal. It approves no
school policy and changes no frozen foundation artefact.

---

## The rule this packet exists to enforce

**Contract approval comes before module coding.** This directory must contain, for
review:

1. the exact **OpenAPI** document for this module's REST API
2. the **JSON Schema** for every request, response and event payload
3. the **Protocol signatures** for every service port this module provides
4. the **error enums** — which `code`/`message_key` pairs this module returns
5. **example fixtures** a consumer suite can assert against

Those are then **frozen in `contracts/manifest.json`** before implementation starts.
A later provider of the same contract must pass the same consumer fixture suite. A
mismatch needs a reviewed contract revision — **not** an invented per-module field
and **not** a local adapter.

## Artefacts for review

| File | Contents |
|---|---|
| `openapi.json` | OpenAPI 3.1; 21 operations across 16 paths, with explicit write fields, nullability, permission and step-up metadata, cursor pagination and the full error surface on every operation |
| `schemas/dtos.schema.json` | 35 closed DTO, request and collection definitions |
| `schemas/events.schema.json` | Both event payloads, and the naming conflict with the frozen envelope |
| `ports.md` | The provided `TimetablePort`, the four consumed ports, the stable session identity, and four gaps in the frozen `RegistryPort` |
| `error-codes.json` | 33 status/code/message-key rows and 7 conflict codes, all reusing the frozen `ErrorCode` enum |
| `fixtures/scenario.json` | The deterministic synthetic baseline: C1/C2, T1, T2, R1, two periods, a holiday, an exam day, an unavailability window and two dated substitutions |
| `fixtures/responses.json` | 12 schema-valid response examples and 2 envelope-valid events, all machine-validated |
| `fixtures/expected-results.json` | 22 proposed acceptance cases and 3 explicitly pending integration cases — **not** test evidence |
| `review-decisions.md` | The decisions requested, with who is affected by each |

## What this module declares

A `ModuleRegistration` in `backend/modules/timetable/registration.py`:

| field | proposed value |
|---|---|
| `id` | `M03` |
| `slug` | `timetable` |
| `api_prefix` | `/api/v1/` (the shared version root, as M01 and M02 use) |
| `api_path_roots` | `timetables/`, `calendar/`, `calendar-exceptions/`, `teacher-unavailability/`, `teacher-schedule/`, `student-schedule/`, `substitutions/`, `sessions/` |
| `permission_codes` | `timetable.read`, `timetable.read_section`, `timetable.read_teacher`, `timetable.read_student`, `timetable.edit`, `timetable.publish`, `timetable.substitute` |
| `consumers` | `access`, `registry`, `platform`, `clock` |
| `scheduled_jobs` | none — M03 owns no background work, and therefore declares no broker and no worker |
| `migration_dependencies` | none |
| `health_checks` | tables queryable; an effective published version exists |

The packet's permission list names `timetable.edit/publish`, `timetable.substitute`
and `timetable.read`. The three additional read codes are the split between a
school-scoped read and a relationship-gated one — the same split M02 makes between
`students.read` and `students.read_record`. Without it, "unrelated class denied"
cannot be expressed. See review item 3.

## Owned records

| Record | Key constraints |
|---|---|
| `TimetableVersion(school, year, effective_from, effective_to, state, version)` | state ∈ draft/published/superseded; one effective published version per date |
| `PeriodTemplate(timetable, day_of_week, slot_code, starts_at_local, ends_at_local)` | unique (timetable, day, slot_code); end strictly after start; no overlap within a weekday, compared half-open |
| `Slot(timetable, period, section, subject, teacher, room_code)` | unique (timetable, section, period) — the packet's "unique version/section/period" |
| `CalendarException(school, date, kind, reason_key, withdrawn, version)` | unique (school, date, kind) |
| `TeacherUnavailable(school, staff, starts_at, ends_at, reason_key, withdrawn, version)` | end strictly after start; half-open for overlap |
| `Substitution(school, date, slot, substitute_teacher, valid_until, reason, withdrawn, version)` | unique (school, date, slot) while not withdrawn |
| `SessionCancellation(school, date, slot, cancelled, reason_key, version)` | **proposed addition** — review item 6 |

Every row carries a UUID `id`, a trusted `school_id` taken from the RequestContext
and never from a body, and an integer `version` on every mutable aggregate.

## Inherited, non-negotiable constraints

These come from the foundation and are already enforced; this module does not
restate or relax them:

- UUID `id`, trusted `school_id`, integer `version` on mutable aggregates
- `expected_version` on every update; stale means **409**
- errors use the frozen envelope: 401 / 403 / 404 / 409 / 422
- **cross-school access is 404, never 403**
- collections return `items` + `next_cursor`; no offset pagination
- UTC instants, Asia/Kolkata civil dates, integer INR paise, decimal-string marks
- audit + outbox appended in the **same transaction** as the write
- Access checks apply to API, service, workers, exports and private files
- client role, school and relationship claims are never trusted
- `ResourceGrant` is server-internal and never accepted from a browser

## Standalone development

```bash
python scripts/dev.py up M03 --profile standalone
python scripts/dev.py migrate M03 --profile standalone
python scripts/dev.py seed M03 --scenario baseline
python scripts/dev.py check M03 --suite standalone
```

Dependency ports bind to deterministic fakes; fake Access denies by default and
evaluates explicit fixture grants. Real authentication and 2FA integration stay
**explicitly pending** until M01 is integrated.

## B00 notes specific to this module

Owns the central timetable. Attendance depends on its periods. Every teaching period
participates in attendance; this is confirmed product behaviour and is not a
granularity question to ask.

## Human gates before this module ships

- **this packet reviewed and frozen in the manifest** ← the gate this proposal is at
- every authorisation rule reviewed before being enabled
- the phase exit gate
- first customer-facing report for each design partner, where applicable
