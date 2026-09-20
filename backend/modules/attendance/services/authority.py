"""Period-teacher gate and Access checks for attendance writes."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible, StateConflict
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts
from contracts.timetable import TeachingAuthorityDTO


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Combines Timetable teaching authority with Access policy."""

    access: object
    timetable: object

    def require_period_action(
        self,
        context: RequestContext,
        *,
        action: str,
        timetable_session_id: UUID,
    ) -> TeachingAuthorityDTO:
        """Authorise marking/submitting one dated period.

        Requires Access permission AND that the actor is the assigned teacher or
        the live substitute. Class-teacher relationship alone is insufficient.
        """
        try:
            authority = self.timetable.get_teaching_authority(context, timetable_session_id)
        except ObjectInaccessible:
            raise
        if not authority.eligible_for_attendance:
            raise StateConflict("attendance.error.period_not_eligible")
        authorised_teachers = {authority.assigned_teacher_id}
        if authority.substitute_teacher_id is not None:
            authorised_teachers.add(authority.substitute_teacher_id)
        if context.actor_id not in authorised_teachers:
            raise ActionDenied("error.action_denied")
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=authority.school_id,
                section_id=authority.section_id,
                subject_id=authority.subject_id,
                effective_date=authority.date,
            ),
        )
        return authority

    def require_school_read(self, context: RequestContext) -> None:
        """Authorise listing periods for the actor's school."""
        self.access.check(
            context,
            "attendance.read",
            ScopeFacts(resource_school_id=context.school_id),
        )
