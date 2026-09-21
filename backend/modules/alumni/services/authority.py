"""Authority helpers for alumni reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible, ValidationFailed
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts
from contracts.values import school_date
from shared.people import actor_is_family

from ..models import AlumniPolicy


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Registry then asks Access. Staff-only actions refuse guardians and students."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_action(self, context: RequestContext, action: str) -> None:
        """Authorise a school-scoped alumni action.

        Fixture non-staff actors (students, guardians, scenario unrelated) are
        denied even when FakeAccess school-scopes would otherwise allow them —
        former parent/teacher grants must not expand into alumni directory
        access. Does not invent production role catalogues.
        """
        if actor_is_family(self.registry, context):
            raise ActionDenied("error.action_denied")
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id,
                effective_date=self.effective_date(),
            ),
        )

    def ensure_student_in_school(self, context: RequestContext, person_id: UUID) -> object:
        """Load student via Registry; other-school is inaccessible."""
        student = self.registry.get_student(context, person_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return student

    def policy_for(self, school_id: UUID) -> AlumniPolicy:
        """Return the school's AlumniPolicy row or raise validation when missing."""
        policy = AlumniPolicy.objects.filter(school_id=school_id).first()
        if policy is None:
            raise ValidationFailed("error.validation_failed")
        return policy

    def require_contact_self_enabled(self, context: RequestContext) -> None:
        """Refuse alumni.contact_self when fixture login policy is off."""
        policy = self.policy_for(context.school_id)
        if not policy.alumni_login_enabled:
            raise ValidationFailed("alumni.error.contact_self_disabled")
        self.require_action(context, "alumni.contact_self")
