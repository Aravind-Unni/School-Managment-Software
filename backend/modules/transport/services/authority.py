"""Authority helpers for transport reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from contracts.values import school_date
from shared import fixtures

READ_RELATIONSHIPS = frozenset({Relationship.SELF, Relationship.GUARDIAN})


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Registry student school then asks Access."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_action(
        self,
        context: RequestContext,
        action: str,
        *,
        student_id: UUID | None = None,
    ) -> None:
        """Authorise a school-scoped transport action; optional student check."""
        school_id = context.school_id
        if student_id is not None:
            student = self.registry.get_student(context, student_id)
            if student.school_id != context.school_id:
                raise ObjectInaccessible("error.object_inaccessible")
            school_id = student.school_id
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=school_id,
                subject_person_id=student_id,
                effective_date=self.effective_date(),
            ),
        )

    def require_participation_read(self, context: RequestContext, student_id: UUID) -> None:
        """Authorise staff list-style read, or self/guardian for one pupil.

        Unrelated guardians get 404 so existence is not confirmed.
        """
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        on = self.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.relationship in READ_RELATIONSHIPS:
            pass
        elif facts.relationship is Relationship.NONE and not self._actor_is_guardian(
            context.actor_id
        ):
            pass
        else:
            raise ObjectInaccessible("error.object_inaccessible")
        self.access.check(
            context,
            "transport.read",
            ScopeFacts(
                resource_school_id=student.school_id,
                subject_person_id=student_id,
                relationship=facts.relationship,
                section_id=facts.section_id,
                effective_date=on,
            ),
        )

    def _actor_is_guardian(self, actor_id: UUID) -> bool:
        """Return True when the actor appears in synthetic guardian links."""
        return any(link.guardian_id == actor_id for link in fixtures.GUARDIAN_LINKS)
