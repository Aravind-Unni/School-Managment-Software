"""Authority helpers for performance reads and staff writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from contracts.values import school_date
from shared.people import is_school_wide_reader

READING_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Registry relationships then asks Access."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_student_read(
        self,
        context: RequestContext,
        student_id: UUID,
        *,
        action: str = "performance.read",
    ) -> None:
        """Authorise own-child or assigned-staff read; inaccessible is 404.

        Unrelated same-school actors and wrong-child guardians get 404 so
        existence is not confirmed. Cross-school is also 404.
        """
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        on = self.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.relationship not in READING_RELATIONSHIPS and not is_school_wide_reader(
            self.access, context, on
        ):
            raise ObjectInaccessible("error.object_inaccessible")
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=student.school_id,
                subject_person_id=student_id,
                relationship=facts.relationship,
                section_id=facts.section_id,
                effective_date=on,
            ),
        )

    def require_staff_action(
        self,
        context: RequestContext,
        action: str,
        *,
        student_id: UUID | None = None,
    ) -> None:
        """Authorise a school-scoped staff write; optional student existence check."""
        school_id = context.school_id
        section_id = None
        relationship = None
        if student_id is not None:
            student = self.registry.get_student(context, student_id)
            if student.school_id != context.school_id:
                raise ObjectInaccessible("error.object_inaccessible")
            on = self.effective_date()
            facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
            section_id = facts.section_id
            relationship = facts.relationship
        else:
            on = self.effective_date()
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=school_id,
                subject_person_id=student_id,
                relationship=relationship,
                section_id=section_id,
                effective_date=on,
            ),
        )

    def is_guardian_or_self(self, context: RequestContext, student_id: UUID) -> bool:
        """Return True when the actor is the pupil or their guardian."""
        on = self.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        return facts.relationship in {Relationship.SELF, Relationship.GUARDIAN}
