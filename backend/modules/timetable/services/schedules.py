"""The read-only schedule views: a class's day, a teacher's day, a pupil's day.

All three go through the same reader, because the packet requires that every
school view uses the same effective source. What differs between them is only who
is allowed to ask and what is added on top -- a teacher's cover duties, a pupil's
subject enrolment.

Does not handle: resolving the schedule. ``reads.py`` does that once.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import StateConflict
from contracts.identity import RequestContext

from .reads import CalendarDay, DayView, ScheduleReader, SessionView


@dataclass(frozen=True, slots=True)
class StudentDay:
    """One pupil's dated schedule, with per-session enrolment."""

    student_id: UUID
    section_id: UUID
    date: date
    day: CalendarDay
    sessions: tuple[tuple[SessionView, bool], ...]


@dataclass(frozen=True, slots=True)
class ScheduleService:
    """Serves the three read-only schedule views."""

    scope: object
    registry: object
    reader: ScheduleReader

    def section_day(
        self,
        context: RequestContext,
        *,
        section_id: UUID,
        on: date,
        student_id: UUID | None,
    ) -> DayView:
        """Return one section's effective schedule for a date.

        Raises StateConflict when no published revision covers the date. A browser
        asking for a schedule that does not exist needs to be told so; the service
        port answers the same question with an empty tuple instead, because a
        consumer asking "what is on" is not making a mistake.
        """
        self.scope.require_section_read(
            context, section_id=section_id, on=on, student_id=student_id
        )
        view = self.reader.day_for_section(
            school_id=context.school_id, section_id=section_id, on=on
        )
        if view.timetable is None:
            raise StateConflict("timetable.error.no_effective_timetable")
        return view

    def teacher_day(
        self, context: RequestContext, *, staff_id: UUID, on: date
    ) -> tuple[CalendarDay, tuple[SessionView, ...]]:
        """Return one staff member's dated periods, including cover duties."""
        self.scope.require_teacher_read(context, staff_id=staff_id, on=on)
        return self.reader.sessions_for_teacher(
            school_id=context.school_id, staff_id=staff_id, on=on
        )

    def student_day(self, context: RequestContext, *, student_id: UUID, on: date) -> StudentDay:
        """Return one pupil's dated schedule, marking the subjects they take.

        Enrolment comes from Registry's SUBJECT-FILTERED roster, asked once per
        distinct subject in the day rather than once per pupil per period. A view
        that ignored the filter would show a pupil a lesson they do not take, and
        would later mark them absent from it.
        """
        _scope, facts = self.scope.require_student_read(context, student_id=student_id, on=on)
        section_id = facts.section_id
        if section_id is None:
            raise StateConflict("timetable.error.no_effective_timetable")

        view = self.reader.day_for_section(
            school_id=context.school_id, section_id=section_id, on=on
        )
        enrolled_subjects = self._enrolled_subjects(
            context, section_id=section_id, on=on, sessions=view.sessions, student_id=student_id
        )
        return StudentDay(
            student_id=student_id,
            section_id=section_id,
            date=on,
            day=view.day,
            sessions=tuple(
                (session, session.dated.subject_id in enrolled_subjects)
                for session in view.sessions
            ),
        )

    def _enrolled_subjects(
        self,
        context: RequestContext,
        *,
        section_id: UUID,
        on: date,
        sessions: tuple[SessionView, ...],
        student_id: UUID,
    ) -> frozenset[UUID]:
        """Return which of the day's subjects this pupil is enrolled in."""
        enrolled: set[UUID] = set()
        for subject_id in sorted({session.dated.subject_id for session in sessions}, key=str):
            roster = self.registry.get_roster(context, section_id, on, subject_id)
            if any(entry.student_id == student_id for entry in roster.students):
                enrolled.add(subject_id)
        return frozenset(enrolled)
