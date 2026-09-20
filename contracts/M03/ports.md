# M03 service ports — PROPOSED, NOT FROZEN

Two lists. What M03 **provides** to other modules, and what it **consumes**. Nothing
here is frozen until the manifest says so.

M03 imports no other module. Every dependency below is a Protocol from
`backend/contracts/ports.py`, bound to a deterministic fake in standalone and to a
real provider in integrated mode.

---

## 1. Provided: `TimetablePort`

M04 attendance is the consumer this exists for. Its exact shape comes from the
packet's "public internal services" list, plus one addition (`get_teaching_authority`)
explained below.

```python
@runtime_checkable
class TimetablePort(Protocol):
    """The central timetable, as another module sees it. Owned by M03."""

    def get_sessions(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
    ) -> tuple[PeriodSessionDTO, ...]:
        """Return every eligible teaching period for a section on a date.

        Published effective periods only. A holiday returns an empty tuple,
        because a holiday has no eligible teaching period; a cancelled period is
        returned with ``cancelled`` true, so the consumer can show it rather than
        silently lose it.
        """

    def get_session(
        self,
        context: RequestContext,
        timetable_session_id: UUID,
    ) -> PeriodSessionDTO:
        """Return one dated period by its stable school-scoped identity.

        Raises ObjectInaccessible for an unknown id AND for one in another
        school, conflating the two.
        """

    def get_calendar(
        self,
        context: RequestContext,
        from_date: date,
        to_date: date,
    ) -> tuple[CalendarDayDTO, ...]:
        """Return whether each date in an inclusive range is a teaching day."""

    def get_teaching_authority(
        self,
        context: RequestContext,
        timetable_session_id: UUID,
    ) -> TeachingAuthorityDTO:
        """Return who may teach one dated period, and until when.

        PROPOSED ADDITION, not in the packet's list. The packet says
        "Timetable revisions and substitutions are authoritative inputs to period
        attendance, including teacher authorization" and "Attendance combines
        this trusted fact with Access policy". That combination needs one
        trusted fact with an expiry on it. Deriving it inside M04 from
        PeriodSessionDTO would put the expiry rule in the consumer, where two
        consumers would eventually disagree about when a substitution lapses.
        """
```

### Stable dated identity

```
timetable_session_id = uuid5(
    TIMETABLE_SESSION_NAMESPACE,
    f"{school_id}:{section_id}:{iso_date}:{slot_code}",
)
```

Derived, not stored. It deliberately excludes the timetable version and the slot
row id, because those change when a revision is published and the identity must
not. Republishing the same weekly grid under a new revision therefore yields the
**same** session ids, which is what stops a revision from creating duplicate
attendance identities.

It includes `slot_code` rather than the period's start time, so a school that moves
P2 from 09:30 to 09:45 in a new revision keeps its attendance continuity.

### Where the Protocol should live

`backend/contracts/ports.py` is shared and frozen. Adding `TimetablePort` to it is a
**shared contract revision**, not a module edit, so this proposal does not make it.
Until a reviewer approves that, M03 exposes the concrete implementation at
`modules.timetable.services.port.TimetableService`, no consumer exists, and the
architecture check keeps it that way. See review-decisions.md item 2.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

Used exactly as frozen. `check` on every write and every read path; `authorize`
where the reason is wanted. M03 supplies `ScopeFacts` and never decides.

`require_recent_2fa` is asked for one action only: publication.

### `RegistryPort` — M02 (fake in standalone)

| Method | What M03 uses it for |
|---|---|
| `get_roster(ctx, section_id, date, subject_id=None)` | Confirming a section exists for this school on a date; and, with `subject_id`, marking whether a pupil is enrolled in the subject a period teaches |
| `get_teaching_assignments(ctx, staff_id, date)` | Resolving which sections a staff member may see, and the non-blocking `teacher_not_assigned` conflict |
| `get_relationships(ctx, actor_id, student_id, date)` | Resolving a pupil's or guardian's relationship to a section before serving its schedule |
| `relationship_facts(ctx, subject_person_id)` | The shared `ScopeResolver` path, for person-scoped reads |

**Four gaps this module hit.** None is worked around; each is recorded here and the
validation that would need it is simply not performed:

1. **No `get_section`.** M03 confirms a section exists by calling `get_roster` and
   treating `ObjectInaccessible` as "unknown section". That conflates an unknown
   section with one the actor may not see, and it fetches a pupil list to answer a
   yes/no question.
2. **No `get_subject`.** A slot's `subject_id` cannot be validated at all. An
   unknown subject id is stored and rendered.
3. **No `get_staff`.** `get_teaching_assignments` returns an empty tuple both for an
   unknown staff member and for a real one who teaches nothing, so a typo'd teacher
   id is indistinguishable from an unassigned teacher. This is why
   `teacher_not_assigned` is proposed as non-blocking: as a blocking rule it would
   reject a valid grid whenever Registry's assignment table lags.
4. **No `get_academic_year`.** A version's `effective_from`/`effective_to` cannot be
   checked against the year it names. `year_id` is stored opaquely.

Proposed additive signatures, owned by M02, for a future reviewed revision:

```python
def get_section(self, context, section_id) -> SectionDTO: ...
def get_subject(self, context, subject_id) -> SubjectDTO: ...
def get_staff(self, context, staff_id) -> StaffDTO: ...
def get_academic_year(self, context, year_id) -> AcademicYearDTO: ...
```

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` and `append_event`, both inside the writing transaction. M03 owns no
background work, so `enqueue` is never called and the module declares no broker or
worker. The notification the packet requires on publication is deliberately **an
outbox event, not a direct send**: "Notify on publication only after transaction
commit; SMS outage cannot prevent timetable publication" is exactly what an outbox
row plus a separate relay gives. M03 does not consume `NotificationPort`.

### `ClockPort`

Every timestamp and every "is this substitution still valid" comparison. No
`datetime.now()` anywhere in the module; decision logic takes the instant as an
argument.

---

## 3. Section scoping, and why this module resolves it itself

The shared `ScopeResolver` answers "how does this actor relate to this **person**".
Most M03 reads are about a **section**, which it cannot answer: asking it about a
section with no subject person yields facts with no relationship, and a
school-scoped rule would then let any authenticated actor read any class's schedule.

M03 therefore resolves section scope in
`modules/timetable/services/scope.py`, using only `RegistryPort`:

* staff → `get_teaching_assignments(actor, date)`, matched on `section_id`
* pupil or guardian → `get_relationships(actor, student_id, date)`, matched on
  `section_ids`, and only while the relationship is active on that date

It folds the answer into `ScopeFacts` and asks Access. It never decides. This is a
module-local resolver, not a change to the shared one; whether the shared resolver
should grow a section-scoped entry point is review item 3.
