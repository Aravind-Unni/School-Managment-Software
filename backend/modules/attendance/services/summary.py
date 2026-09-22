"""Period-based attendance summaries from timetable eligibility + marks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from uuid import UUID

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from contracts.timetable import AttendanceSummaryDTO
from shared.people import system_actor_id

from ..models import AttendanceEntry, AttendanceStatus


@dataclass(frozen=True, slots=True)
class SummaryService:
    """Build eligible/marked counts without inventing a percentage formula."""

    access: object
    registry: object
    timetable: object
    clock: object

    def get_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date,
        subject_id: UUID | None = None,
    ) -> AttendanceSummaryDTO:
        """Return period counts for one pupil. percentage stays None."""
        self._authorise(context, student_id, from_date, to_date)
        counts = _Counts()
        for _day, _subject, status in self._walk(
            context, student_id, from_date, to_date, subject_id
        ):
            counts.add(status)
        return AttendanceSummaryDTO(
            unit="period",
            student_id=student_id,
            from_date=from_date,
            to_date=to_date,
            subject_id=subject_id,
            eligible=counts.eligible,
            marked=counts.marked,
            present=counts.present,
            absent=counts.absent,
            late=counts.late,
            excused=counts.excused,
            unmarked=counts.eligible - counts.marked,
            percentage=None,
            policy_version=None,
            updated_at=self.clock.now(),
        )

    def breakdown(
        self, context: RequestContext, student_id: UUID, from_date: date, to_date: date
    ) -> dict:
        """Return the same period counts split by subject and by month.

        One walk over the pupil's timetable, so both views always add up to the
        same totals as ``get_summary`` for the range.
        """
        self._authorise(context, student_id, from_date, to_date)
        by_subject: dict[UUID, _Counts] = {}
        by_month: dict[str, _Counts] = {}
        total = _Counts()
        for day, subject, status in self._walk(context, student_id, from_date, to_date, None):
            by_subject.setdefault(subject, _Counts()).add(status)
            by_month.setdefault(day.strftime("%Y-%m"), _Counts()).add(status)
            total.add(status)
        return {
            "total": total.to_wire(),
            "by_subject": {str(key): value.to_wire() for key, value in by_subject.items()},
            "by_month": {key: by_month[key].to_wire() for key in sorted(by_month)},
        }

    def _authorise(
        self, context: RequestContext, student_id: UUID, from_date: date, to_date: date
    ) -> None:
        """Check the range and that the reader may see this pupil's attendance."""
        if to_date < from_date:
            raise ValidationFailed("attendance.error.date_range_invalid")
        if (to_date - from_date).days > 400:
            raise ValidationFailed("attendance.error.date_range_invalid")

        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        facts = self.registry.get_relationships(context, context.actor_id, student_id, to_date)
        # Staff school-scoped read OR self/guardian relationship.
        if facts.relationship in {Relationship.SELF, Relationship.GUARDIAN}:
            self.access.check(
                context,
                "attendance.read_student",
                ScopeFacts(
                    resource_school_id=context.school_id,
                    subject_person_id=student_id,
                    relationship=facts.relationship,
                    effective_date=to_date,
                ),
            )
        else:
            self.access.check(
                context,
                "attendance.read",
                ScopeFacts(resource_school_id=context.school_id),
            )

    def _walk(
        self,
        context: RequestContext,
        student_id: UUID,
        from_date: date,
        to_date: date,
        subject_id: UUID | None,
    ):
        """Yield (date, subject id, status or None) for every period the pupil was due at.

        The reader was authorised by ``_authorise``. The day-by-day lookups
        (class timetable, rosters) are internal, so they run as the school's
        read-only jobs account rather than needing the reader to hold
        class-wide timetable rights a parent never has.
        """
        lookup = replace(context, actor_id=system_actor_id(context.school_id))
        # One query for every mark this pupil has, keyed by timetable period.
        marks = dict(
            AttendanceEntry.objects.filter(
                session__school_id=context.school_id, student_id=student_id
            )
            .exclude(status=AttendanceStatus.UNMARKED)
            .values_list("session__timetable_session_id", "status")
        )
        rosters: dict[tuple, bool] = {}
        known_section: UUID | None = None
        cursor = from_date
        while cursor <= to_date:
            if known_section is not None:
                # Weekends, holidays and days before the timetable starts have
                # no periods for the pupil's class: skip them without asking
                # Registry which class the pupil was in.
                periods = self.timetable.get_sessions(lookup, known_section, cursor)
                if not periods:
                    cursor += timedelta(days=1)
                    continue
                section_id = self._section_on(lookup, student_id, cursor)
                if section_id is not None and section_id != known_section:
                    periods = self.timetable.get_sessions(lookup, section_id, cursor)
            else:
                section_id = self._section_on(lookup, student_id, cursor)
                periods = (
                    self.timetable.get_sessions(lookup, section_id, cursor)
                    if section_id is not None
                    else []
                )
            if section_id is None:
                cursor += timedelta(days=1)
                continue
            known_section = section_id
            for period in periods:
                if period.cancelled:
                    continue
                if subject_id is not None and period.subject_id != subject_id:
                    continue
                key = (section_id, cursor, period.subject_id)
                if key not in rosters:
                    roster = self.registry.get_roster(
                        lookup, section_id, cursor, subject_id=period.subject_id
                    )
                    rosters[key] = any(r.student_id == student_id for r in roster.students)
                if not rosters[key]:
                    continue
                yield cursor, period.subject_id, marks.get(period.timetable_session_id)
            cursor += timedelta(days=1)

    def _section_on(self, context: RequestContext, student_id: UUID, on: date) -> UUID | None:
        """Return the pupil's section on a date, as Registry reports it."""
        try:
            facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        except ObjectInaccessible:
            return None
        return facts.section_id


class _Counts:
    """Running period counts: due (eligible), and each mark kind."""

    def __init__(self) -> None:
        """Start at zero."""
        self.eligible = self.present = self.absent = self.late = self.excused = 0

    @property
    def marked(self) -> int:
        """Periods with any mark."""
        return self.present + self.absent + self.late + self.excused

    def add(self, status: str | None) -> None:
        """Count one due period and its mark (None when not marked yet)."""
        self.eligible += 1
        if status == AttendanceStatus.PRESENT:
            self.present += 1
        elif status == AttendanceStatus.ABSENT:
            self.absent += 1
        elif status == AttendanceStatus.LATE:
            self.late += 1
        elif status == AttendanceStatus.EXCUSED:
            self.excused += 1

    def to_wire(self) -> dict:
        """Return counts plus attended % (present + late over marked, excused left out)."""
        counted = self.marked - self.excused
        percent = f"{(self.present + self.late) * 100 / counted:.2f}" if counted > 0 else None
        return {
            "due": self.eligible,
            "marked": self.marked,
            "present": self.present,
            "absent": self.absent,
            "late": self.late,
            "excused": self.excused,
            "percentage": percent,
        }
