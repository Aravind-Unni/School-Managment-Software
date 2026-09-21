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

        # The reader is authorised for this pupil above. The day-by-day lookups
        # below (class timetable, rosters) are internal, so they run as the
        # school's read-only jobs account rather than needing the reader to
        # hold class-wide timetable rights a parent never has.
        lookup = replace(context, actor_id=system_actor_id(context.school_id))
        eligible = 0
        present = absent = late = excused = 0
        cursor = from_date
        while cursor <= to_date:
            section_id = self._section_on(lookup, student_id, cursor)
            if section_id is None:
                cursor += timedelta(days=1)
                continue
            periods = self.timetable.get_sessions(lookup, section_id, cursor)
            for period in periods:
                if period.cancelled:
                    continue
                if subject_id is not None and period.subject_id != subject_id:
                    continue
                roster = self.registry.get_roster(
                    lookup, section_id, cursor, subject_id=period.subject_id
                )
                on_roster = any(r.student_id == student_id for r in roster.students)
                if not on_roster:
                    continue
                eligible += 1
                entry = (
                    AttendanceEntry.objects.filter(
                        session__school_id=context.school_id,
                        session__timetable_session_id=period.timetable_session_id,
                        student_id=student_id,
                    )
                    .exclude(status=AttendanceStatus.UNMARKED)
                    .first()
                )
                if entry is None:
                    continue
                if entry.status == AttendanceStatus.PRESENT:
                    present += 1
                elif entry.status == AttendanceStatus.ABSENT:
                    absent += 1
                elif entry.status == AttendanceStatus.LATE:
                    late += 1
                elif entry.status == AttendanceStatus.EXCUSED:
                    excused += 1
            cursor += timedelta(days=1)

        marked = present + absent + late + excused
        return AttendanceSummaryDTO(
            unit="period",
            student_id=student_id,
            from_date=from_date,
            to_date=to_date,
            subject_id=subject_id,
            eligible=eligible,
            marked=marked,
            present=present,
            absent=absent,
            late=late,
            excused=excused,
            unmarked=eligible - marked,
            percentage=None,
            policy_version=None,
            updated_at=self.clock.now(),
        )

    def _section_on(self, context: RequestContext, student_id: UUID, on: date) -> UUID | None:
        """Return the pupil's section on a date, as Registry reports it."""
        try:
            facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        except ObjectInaccessible:
            return None
        return facts.section_id
