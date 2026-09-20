# M03 review decisions — nothing is approved by this file existing

Writing a proposal is not approving it. Every row below needs a named reviewer and
a date before `contracts/M03` is added to `contracts/revision.json` and hashed into
the manifest. Until then M03's status stays `not_started` and no module code is
written.

Source identity this proposal was produced against, read from the checkout rather
than supplied:

| Item | Observed value |
|---|---|
| Repository | https://github.com/Aravind-Unni/School-Managment-Software |
| Branch | `m03/timetable-calendar` |
| Branched from | `aab4b6d79cc4c8ca9e10fb63b7b9d39c5cd8c81a` (`main`) |
| Manifest revision | `school-contracts-v4`, status `reviewed`, 20 frozen entries |
| M03 manifest status | `not_started`; `contracts/M03` contained only `PACKET.md` |
| Foundation check at session start | `dev.py check M00 --suite contracts` passed: manifest current, 7 architecture checks, 105 shared contract tests |
| `dev.py doctor` | exits 2 — no container engine on this machine |

---

## Prerequisites the reviewer should know about, not work around

1. **B00's own gate is still open.** `docs/foundation/progress.md` records that the
   foundation was merged without peer review with four acceptance criteria
   unverified, and that the container path has never been executed by anyone. M03
   inherits that. Nothing in this module can close it.
2. **No container engine here.** `doctor` exits 2. The standalone suite (real
   PostgreSQL) and the browser suite therefore cannot run on this machine and will
   be recorded `not-run`, never as passing. CI runs them; its result attaches to the
   commit it tested and to no other.
3. **M02 is merged but only step 1 of 4 is implemented.** M03 standalone binds the
   deterministic fake Registry, so this does not block it — but it does mean the
   real provider for four of M03's inputs does not exist yet, and the three PENDING
   integration cases in `fixtures/expected-results.json` stay pending.
4. **Node here is v20.19.5; `frontend/package.json` requires `^22.22.2 || >=24`.**
   The frontend unit, typecheck and build steps will not run on this machine either.

---

## Decisions requested

Each row: what the packet says, what is proposed, and who is affected if it is
accepted. A "no" on any row is cheaper now than after the code exists.

### 1. Event names conflict with the frozen envelope

The packet asks for `TimetablePublished.v1` and `SubstitutionAssigned.v1`. The
frozen `contracts/common/event-envelope.schema.json` constrains `event_type` to
`^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` — lowercase, exactly two segments — and
`EventEnvelope.__post_init__` enforces the dot. Both packet names are rejected by
the shared schema. M02 recorded the same conflict for its four event names and left
it unresolved, because M02 step 1 emits no event. **M03 emits both of its events, so
it cannot leave this open.**

**Proposed:** emit `timetable.published` and `timetable.substitution_assigned`, and
record the mapping to the packet's names in `schemas/events.schema.json`. This keeps
the frozen envelope untouched.

**Alternative, if the reviewer wants the packet names verbatim:** that is a revision
of a shared frozen schema, affecting M01, M02, M14's outbox and every future
consumer, and it must be reviewed as such. It is not a change M03 may make.

*Affected:* Platform outbox, every event consumer, M02's identical open item.

### 2. Where `TimetablePort` lives

`backend/contracts/ports.py` is shared and frozen. The packet requires M03 to
provide `Timetable.get_sessions`, `get_session` and `get_calendar` as in-process
services, and M04 will consume them.

**Proposed:** implement the concrete service inside M03 now
(`modules.timetable.services.port`), and add the `TimetablePort` Protocol to
`backend/contracts/ports.py` **only when a reviewer approves it**, as an additive
shared revision. No consumer exists yet, so nothing is blocked by deferring it.

*Affected:* shared contracts owner, M04.

### 3. Section-scoped authorisation has no shared resolver

The shared `ScopeResolver` resolves actor-to-**person** relationships. Almost every
M03 read is scoped to a **section**. Asking the shared resolver about a section with
no subject person produces facts with no relationship, and a school-scoped policy
rule would then let any authenticated actor read any class's schedule — which fails
the packet's own "unrelated class denied" acceptance test.

**Proposed:** M03 resolves section scope itself in `services/scope.py`, using only
the frozen `RegistryPort` (`get_teaching_assignments` for staff,
`get_relationships` for pupils and guardians), folds the answer into `ScopeFacts`,
and asks Access. It decides nothing. Whether the **shared** resolver should grow a
section entry point is a separate shared revision; every module after M03 that is
section-scoped — M04, M05 — will need the same thing, so deciding it now is cheaper.

*Affected:* shared resolver owner, M04, M05.

### 4. `teacher_not_assigned` proposed as NON-blocking

Registry owns teaching assignments, and the packet says assignments "come through
registry ports". A slot whose teacher has no dated assignment for that section and
subject is therefore detectable.

**Proposed: report it, do not block publication.** Two reasons. Schools commonly
build the grid before the assignment table is complete, so blocking makes the
timetable depend on another module's data-entry order. And the frozen
`get_teaching_assignments` returns an empty tuple both for an unknown staff member
and for a real one who teaches nothing, so as a blocking rule it cannot tell a typo
from a legitimate gap. Every other conflict code is blocking.

*Affected:* the academic head's publish flow; M02 if the reviewer prefers blocking,
because it would then need gap 3 below closed first.

### 5. Rooms

The seeded scenario names "room R1", but rooms are not among the module's owned
records, and no room conflict is in the packet's validation list.

**Proposed:** an optional free-text `room_code` on `Slot`, with **no** Room
aggregate and **no** room double-booking detection. Modelling rooms properly, and
detecting a room clash, is a separate story.

*Affected:* nobody outside M03. Reject it and the seed simply drops the room.

### 6. A session cancellation record, which the packet's record list does not name

`PeriodSessionDTO` carries `cancelled`, the UI must "show cancelled sessions", and
"a day override does not mutate the recurring schedule". A whole-day holiday is
already covered by `CalendarException`. Cancelling **one period** on one date has no
record in the owned list.

**Proposed:** add `SessionCancellation(school_id, date, slot, cancelled,
reason_key, version)`, keyed by the stable dated session identity, written by
`PUT /sessions/{id}/cancellation`. It creates no timetable revision.

*Affected:* M04 — a cancelled period is reported with
`eligible_for_attendance` false rather than disappearing.

### 7. How long a substitution lasts

The packet says a substitution "may support attendance access for that exact
date/slot", must expire, and must never become a standing class permission. It does
not say when it lapses.

**Proposed:** `valid_until` defaults to the **end of the session's own civil day at
the school** (Asia/Kolkata), as an exclusive instant. A caller may set it earlier
but never later than that boundary, and never earlier than the period's own end;
both are 422. The default is not the period's end instant because a teacher
commonly marks the register after the lesson, sometimes at the end of the day.

**This is the one row that is closest to school policy.** If the school's rule is
different — the period end, or a fixed grace window — say so and it becomes data.

*Affected:* M04's authorisation window.

### 8. Publication is forward-only

**Proposed:** publishing a version whose `effective_from` is not strictly later than
the currently effective version's `effective_from` is refused
(`timetable.error.effective_from_not_after_effective`). Publishing closes the
previous version's `effective_to` at the day before, and leaves it readable and
listable forever.

The reason to refuse retrospective publication: a past register was taken against
the grid that was effective then, and silently rewriting it would make historical
attendance unreconcilable. If a school genuinely needs to correct the past, that is
a reviewed correction flow, not a publish.

*Affected:* M04 reconciliation; the academic head.

### 9. What makes a date a school day

`get_calendar` must answer `is_school_day`. Deciding that "schools teach Monday to
Friday", or Saturday, would be inventing school policy.

**Proposed:** a date is a school day when the effective published version defines at
least one period for that weekday **and** no `holiday` exception is in force. The
weekly pattern is entirely the school's own `PeriodTemplate` rows. A date with no
periods reports `is_school_day` false with `timetable.reason.no_periods`; a holiday
reports `timetable.reason.holiday`. An `exam` or `event` exception does **not** make
a date a non-teaching day.

There is deliberately **no working-day override** — no way to say "this Sunday is a
working day" — because the packet does not name one and it would be a guess. If the
school needs it, it is a fourth calendar kind and one more branch in this rule.

*Affected:* M04; every schedule view.

### 10. Four things M03 cannot validate, and does not pretend to

The frozen `RegistryPort` has no `get_section`, `get_subject`, `get_staff` or
`get_academic_year`. So:

* a section is confirmed only indirectly, by `get_roster` raising;
* **a slot's `subject_id` is not validated at all**;
* an unknown teacher id is indistinguishable from an unassigned teacher;
* **a version's effective range is not checked against the year it names.**

No workaround is in this proposal. The additive signatures are written out in
`ports.md`; they are M02's to provide, under a reviewed revision.

*Affected:* M02 (as provider), M03, and every later module with the same need.

### 11. Step-up: publication only

**Proposed:** `timetable.publish` requires a second factor asserted within the
reviewed 300-second window — the same number M02 uses, held as data in
`fixture_policy.py`. `timetable.edit` and `timetable.substitute` do not. Substitution
is daily work done in a corridor minutes before a lesson; requiring a TOTP code for
it would push schools towards shared logins, which is worse for security than the
thing it buys.

*Affected:* the academic head and the daily substitution flow.

### 12. Period templates belong to the version, not to the school

The owned-record list gives `PeriodTemplate(day, start, end, slot_code)` with no
owner named.

**Proposed:** it is a child of `TimetableVersion`. A school that moves the bell does
so in a new revision, and the old revision must keep the bell times a past register
was taken under. Making it school-level would silently rewrite history.

Because of this, the stable dated session identity keys on `slot_code` and not on
the period's start time — so moving P2 from 09:30 to 09:45 does not orphan
attendance.

*Affected:* M04.

### 13. `timetable_version` in `PeriodSessionDTO` is ambiguous

The packet lists the field without saying whether it is the version row's UUID or
the aggregate's integer version.

**Proposed:** emit both — `timetable_id` (UUID) and `timetable_version` (integer) —
so a consumer can name the exact revision without a second call.

*Affected:* M04.

### 14. Calendar kinds

**Proposed:** `holiday`, `exam`, `event`, and nothing else. The packet names
holidays and exam periods; `event` covers a school function that is neither.
Anything further is the school's to define.

*Affected:* the calendar UI.

---

## What this proposal does not touch

* No shared file under `backend/contracts`, `backend/shared`, `scripts/` or
  `contracts/common` is modified.
* No frozen hash is moved. `contracts/manifest.json` is regenerated only after a
  freeze decision, and `contracts/M03` is absent from it today.
* No guard is weakened, no test is modified, no threshold is changed.
* No other module is imported, and no other business app is installed.
* There is no `DELETE` anywhere in the API. Exceptions, unavailability and
  substitutions are **withdrawn**, because a published schedule or a past register
  may already cite them.

## Approving this

Approval means: name the reviewer and the date, add `M03` to
`contracts/revision.json` under `frozen_modules`, regenerate
`contracts/manifest.json` with `scripts/contract_manifest.py --update`, and commit
that as the freeze. Only then are M03's tests written — from the frozen contract,
without reading an implementation, because there will not be one yet.
