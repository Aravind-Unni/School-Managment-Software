"""Authority helpers for communications reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts
from contracts.values import school_date

from ..fixture_ids import NON_STAFF_ACTORS
from ..models import CommunicationsPolicy


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Access for school-scoped communications actions."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def require_action(self, context: RequestContext, action: str) -> None:
        """Authorise a school-scoped action; deny known non-staff fixture actors."""
        if context.actor_id in NON_STAFF_ACTORS:
            raise ActionDenied("error.action_denied")
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id,
                effective_date=self.effective_date(),
            ),
        )

    def require_sms_configure(self, context: RequestContext) -> None:
        """Authorise sms.configure; optional recent 2FA per fixture policy."""
        self.require_action(context, "sms.configure")
        policy = CommunicationsPolicy.objects.filter(school_id=context.school_id).first()
        if policy is not None and policy.sms_configure_requires_2fa:
            self.access.require_recent_2fa(context, max_age_seconds=300)

    def ensure_person_in_school(self, context: RequestContext, person_id: UUID) -> object:
        """Load student via Registry; other-school is inaccessible."""
        student = self.registry.get_student(context, person_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return student
