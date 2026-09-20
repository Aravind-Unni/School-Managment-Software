"""The service M04 attendance will consume in-process.

Shaped exactly as ``contracts/M03/ports.md`` proposes, so binding it to a
``TimetablePort`` Protocol later is a declaration and not a rewrite.

Authorisation runs HERE, not only in the views, so a worker or an export calling
the same service gets the same decision an HTTP caller would.

Does not handle: transport. This is an in-process call in a modular monolith.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext

from ..dtos import CalendarDayDTO, PeriodSessionDTO, TeachingAuthorityDTO
from .calendar import require_bounded_range
from .reads import ScheduleReader, SessionView


@dataclass(frozen=True, slots=True)
class TimetableService:
    """The timetable as another module sees it."""

    scope: object
    clock: object
    reader: ScheduleReader

    def get_sessions(
        self, context: RequestContext, section_id: UUID, effective_date: date
    ) -> tuple[PeriodSessionDTO, ...]:
        """Return every eligible teaching period for a section on a date.

        Published effective periods only. A holiday returns an empty tuple,
        because a holiday has no eligible teaching period; a cancelled period is
        returned with ``cancelled`` true, so the consumer can show it rather than
        silently lose it.
        """
        self.scope.require_section_read(context, section_id=section_id, on=effective_date)
        view = self.reader.day_for_section(
            school_id=context.school_id, section_id=section_id, on=effective_date
        )
        return tuple(session_to_dto(session) for session in view.sessions)

    def get_session(
        self, context: RequestContext, timetable_session_id: UUID
    ) -> PeriodSessionDTO:
        """Return one dated period by its stable identity.

        Raises ObjectInaccessible for an unknown id, for one in another school,
        and for one on a date that is not a teaching day -- the three are
        deliberately indistinguishable, so a probe learns nothing.
        """
        session = self._require_session(context, timetable_session_id)
        return session_to_dto(session)

    def get_calendar(
        self, context: RequestContext, from_date: date, to_date: date
    ) -> tuple[CalendarDayDTO, ...]:
        """Return whether each date in an inclusive range is a teaching day."""
        self.scope.require_school_action(context, "timetable.read")
        require_bounded_range(from_date, to_date)
        return tuple(
            CalendarDayDTO(
                date=day.date,
                is_school_day=day.is_school_day,
                reason_key=day.reason_key,
                kinds=day.kinds,
            )
            for day in self.reader.calendar_days(
                school_id=context.school_id, from_date=from_date, to_date=to_date
            )
        )

    def get_teaching_authority(
        self, context: RequestContext, timetable_session_id: UUID
    ) -> TeachingAuthorityDTO:
        """Return who may teach one dated period, and until when.

        Answers rather than raising for a period that exists but is not eligible:
        a holiday or a cancellation gets ``eligible_for_attendance`` false, which
        M04 can act on, where a 404 would be indistinguishable from a bad id.

        A substitution is reported ONLY while it is still live. This is the one
        place expiry is applied -- the schedule views keep showing the substitute,
        because they record who taught, not who is currently authorised.
        """
        session, day = self.reader.session_ignoring_calendar(
            school_id=context.school_id, session_id=timetable_session_id
        )
        if session is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self.scope.require_section_read(
            context, section_id=session.dated.section_id, on=session.dated.date
        )

        live = (
            session.substitution_valid_until is not None
            and self.clock.now() < session.substitution_valid_until
        )
        return TeachingAuthorityDTO(
            timetable_session_id=session.dated.timetable_session_id,
            school_id=session.dated.school_id,
            section_id=session.dated.section_id,
            subject_id=session.dated.subject_id,
            date=session.dated.date,
            assigned_teacher_id=session.dated.teacher_id,
            substitute_teacher_id=session.substitute_teacher_id if live else None,
            substitution_valid_until=session.substitution_valid_until if live else None,
            cancelled=session.cancelled,
            eligible_for_attendance=bool(
                day is not None and day.is_school_day and not session.cancelled
            ),
        )

    def get_sessions_for_staff(
        self,
        context: RequestContext,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[PeriodSessionDTO, ...]:
        """Return dated periods where staff is assigned or covering as substitute."""
        self.scope.require_school_action(context, "timetable.read")
        _day, sessions = self.reader.sessions_for_teacher(
            school_id=context.school_id, staff_id=staff_id, on=effective_date
        )
        return tuple(session_to_dto(session) for session in sessions)

    def _require_session(
        self, context: RequestContext, timetable_session_id: UUID
    ) -> SessionView:
        """Return a session the actor may see, or raise ObjectInaccessible."""
        session = self.reader.session_by_identity(
            school_id=context.school_id, session_id=timetable_session_id
        )
        if session is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self.scope.require_section_read(
            context, section_id=session.dated.section_id, on=session.dated.date
        )
        return session


def session_to_dto(session: SessionView) -> PeriodSessionDTO:
    """Render one reader session as the frozen DTO shape."""
    dated = session.dated
    return PeriodSessionDTO(
        timetable_session_id=dated.timetable_session_id,
        school_id=dated.school_id,
        section_id=dated.section_id,
        date=dated.date,
        slot_id=dated.slot_id,
        slot_code=dated.slot_code,
        subject_id=dated.subject_id,
        assigned_teacher_id=dated.teacher_id,
        substitute_teacher_id=session.substitute_teacher_id,
        starts_at=dated.starts_at,
        ends_at=dated.ends_at,
        starts_at_local=dated.starts_at_local,
        ends_at_local=dated.ends_at_local,
        cancelled=session.cancelled,
        cancellation_reason_key=session.cancellation_reason_key,
        room_code=dated.room_code,
        timetable_id=session.timetable_id,
        timetable_version=session.timetable_version,
    )
