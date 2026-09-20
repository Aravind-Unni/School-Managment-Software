"""Timetable and attendance DTOs shared across modules.

Moved into the frozen contracts package when M04 became the first consumer of
``TimetablePort``. Shapes match the frozen M03/M04 JSON Schemas. No ORM, no
Django.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PeriodSessionDTO:
    """One dated teaching period, with a school-scoped identity stable across revisions."""

    timetable_session_id: UUID
    school_id: UUID
    section_id: UUID
    date: date
    slot_id: UUID
    slot_code: str
    subject_id: UUID
    assigned_teacher_id: UUID
    substitute_teacher_id: UUID | None
    starts_at: datetime
    ends_at: datetime
    starts_at_local: time
    ends_at_local: time
    cancelled: bool
    cancellation_reason_key: str | None
    room_code: str | None
    timetable_id: UUID
    timetable_version: int


@dataclass(frozen=True, slots=True)
class CalendarDayDTO:
    """Whether one date is a teaching day, and why not when it is not."""

    date: date
    is_school_day: bool
    reason_key: str | None
    kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TeachingAuthorityDTO:
    """Who may teach one dated period, and until when.

    A fact for attendance to combine with Access policy, not a decision.
    ``eligible_for_attendance`` is false on a holiday, cancelled period, or a
    date outside every published effective range.
    """

    timetable_session_id: UUID
    school_id: UUID
    section_id: UUID
    subject_id: UUID
    date: date
    assigned_teacher_id: UUID
    substitute_teacher_id: UUID | None
    substitution_valid_until: datetime | None
    cancelled: bool
    eligible_for_attendance: bool


@dataclass(frozen=True, slots=True)
class AttendanceSummaryDTO:
    """Period-based attendance counts for one pupil in a date range.

    ``percentage`` and ``policy_version`` stay None until a calculation version
    is configured. Counts are always returned.
    """

    unit: str
    student_id: UUID
    from_date: date
    to_date: date
    eligible: int
    marked: int
    present: int
    absent: int
    late: int
    excused: int
    unmarked: int
    updated_at: datetime
    subject_id: UUID | None = None
    percentage: str | None = None
    policy_version: str | None = None
