"""The shapes M03 hands to another module in-process.

These mirror ``contracts/M03/schemas/dtos.schema.json`` exactly. They live here,
not in ``backend/contracts``, on purpose: that package is shared and frozen, and
adding ``TimetablePort`` and its DTOs to it is an additive SHARED revision, which
is review item 2. No consumer exists yet, so nothing is blocked by deferring it,
and the architecture check keeps other modules out of here meanwhile.

Does not handle: the browser wire shape. ``api/wire.py`` renders that, from the
same reader output, so the two cannot drift.
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
    """Who may record attendance for one dated period, and until when.

    The trusted fact M04 combines with Access policy. It is a fact, not a
    decision: this module says who is timetabled and whether a substitution is
    still live, and attendance decides what that permits.

    ``eligible_for_attendance`` is false on a holiday, for a cancelled period,
    and for a date outside every published effective range.
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
