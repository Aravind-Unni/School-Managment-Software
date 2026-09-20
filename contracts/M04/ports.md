# M04 service ports — PROPOSED, NOT FROZEN

What M04 **provides** and what it **consumes**. Nothing here is frozen until the
manifest says so.

M04 imports no other module. Dependencies are Protocols from
`backend/contracts/ports.py` (or proposed additions), bound to deterministic
fakes in standalone.

---

## 1. Provided: `AttendancePort`

```python
@runtime_checkable
class AttendancePort(Protocol):
    """Period attendance facts for other modules. Owned by M04."""

    def get_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date,
        subject_id: UUID | None = None,
    ) -> AttendanceSummaryDTO:
        """Return period-based counts for one pupil in an inclusive date range.

        ``eligible`` is non-cancelled scheduled teaching periods during the
        pupil's effective class and subject enrolment, including periods with no
        attendance row yet. ``marked = present+absent+late+excused``;
        ``unmarked = eligible - marked``. Counts are always returned;
        ``percentage`` and ``policy_version`` are null until a calculation
        version is configured. Never infers daily attendance or late/excused
        weights.

        Raises ObjectInaccessible for an unknown or other-school student.
        """
```

`AttendanceSummaryDTO` matches `schemas/dtos.schema.json` (`unit` is always
`"period"`).

Where the Protocol should live: `backend/contracts/ports.py` is shared and
frozen. Adding `AttendancePort` is an additive **shared** revision (review item
2). Until approved, the concrete service lives at
`modules.attendance.services.port.AttendanceService`.

---

## 2. Consumed

### `AccessPort` — M01 (fake in standalone)

| Action | When |
|---|---|
| `attendance.read` | List periods, read summary (self/guardian scoped for pupils) |
| `attendance.mark` | Create draft / save entries — plus dated period assignment check |
| `attendance.submit` | Submit — recheck assignment |
| `attendance.correct` | Corrections — scoped privilege, proposed recent 2FA |

A general class assignment alone does **not** authorise every period. M04
resolves effective teacher from Timetable (`assigned` or live `substitute`) and
folds `{resource_school_id, section_id, subject_id, effective_date}` into
`ScopeFacts`, then asks Access. Period-teacher match is an additional module
gate: Access permission without that exact dated assignment is still denied.

### `RegistryPort` — M02 (fake in standalone)

| Method | Use |
|---|---|
| `get_roster(ctx, section_id, date, subject_id=...)` | Subject-filtered roster snapshot on create; enrolment membership on save |
| `get_student` | Summary subject existence / school isolation |
| `get_relationships` | Guardian/self summary reads |
| `get_teaching_assignments` | Not used to authorise period marking (Timetable substitution is authoritative for the dated period) |

### `TimetablePort` — M03 (fake in standalone) — **PROPOSED SHARED ADDITION**

M03 implemented the concrete service but deferred the Protocol (M03 review item
2) because no consumer existed. M04 is that consumer.

```python
@runtime_checkable
class TimetablePort(Protocol):
    def get_sessions(self, context, section_id, effective_date) -> tuple[PeriodSessionDTO, ...]: ...
    def get_session(self, context, timetable_session_id) -> PeriodSessionDTO: ...
    def get_calendar(self, context, from_date, to_date) -> tuple[CalendarDayDTO, ...]: ...
    def get_teaching_authority(self, context, timetable_session_id) -> TeachingAuthorityDTO: ...
```

DTO shapes match `modules.timetable.dtos` / frozen M03 schemas. Standalone binds
`FakeTimetable` in `backend/shared/fakes/` that validates the same schemas.
Moving DTOs into `backend/contracts` is part of the same shared revision (review
item 2).

### `PlatformPort` — M14 (test adapter in standalone)

`record_audit` + `append_event` in the writing transaction. No owned jobs; no
broker. SMS downtime cannot block attendance because M04 does not call
`NotificationPort`.

### `ClockPort`

Every timestamp and substitution-liveness comparison. No `datetime.now()` in
decision logic.

---

## 3. Period authorisation (module-local)

1. Resolve `TeachingAuthorityDTO` for the `timetable_session_id`.
2. Require `eligible_for_attendance`.
3. Require `context.actor_id` equals `assigned_teacher_id`, or equals live
   `substitute_teacher_id`.
4. Ask Access for the action with section/subject scope facts.

Class-teacher relationship alone never skips step 3.
