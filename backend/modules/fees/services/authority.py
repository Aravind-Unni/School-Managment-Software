"""Authority helpers for fee ledger reads and staff writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from contracts.values import school_date
from shared.people import actor_is_family

STATEMENT_RELATIONSHIPS = frozenset({Relationship.SELF, Relationship.GUARDIAN})

TWO_FACTOR_MAX_AGE_SECONDS = 300


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Registry relationships then asks Access."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_staff_action(
        self,
        context: RequestContext,
        action: str,
        *,
        student_id: UUID | None = None,
        require_2fa: bool = False,
    ) -> None:
        """Authorise a school-scoped finance write; optional student check."""
        if require_2fa:
            self.access.require_recent_2fa(context, max_age_seconds=TWO_FACTOR_MAX_AGE_SECONDS)
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

    def require_statement_read(self, context: RequestContext, student_id: UUID) -> None:
        """Authorise own/guardian or finance-staff statement read.

        Unrelated guardians (relationship NONE but actor is a known guardian of
        someone else) get 404 so existence is not confirmed.
        """
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        on = self.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.relationship in STATEMENT_RELATIONSHIPS:
            pass
        elif facts.relationship is Relationship.NONE and not self._actor_is_family(context):
            pass
        else:
            raise ObjectInaccessible("error.object_inaccessible")
        self.access.check(
            context,
            "fees.read",
            ScopeFacts(
                resource_school_id=student.school_id,
                subject_person_id=student_id,
                relationship=facts.relationship,
                section_id=facts.section_id,
                effective_date=on,
            ),
        )

    def require_staff_read(self, context: RequestContext) -> None:
        """Authorise school-scoped finance list reads (overdue, collections)."""
        self.access.check(
            context,
            "fees.read",
            ScopeFacts(
                resource_school_id=context.school_id,
                effective_date=self.effective_date(),
            ),
        )

    def _actor_is_family(self, context: RequestContext) -> bool:
        """Return True when the actor is a guardian or student in Registry.

        Such an actor with no relationship to the student gets a 404, so the
        student's existence is not confirmed to another family.
        """
        return actor_is_family(self.registry, context)
