"""Authority helpers for library reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from contracts.values import school_date
from shared.people import actor_kind

OWN_RELATIONSHIPS = frozenset({Relationship.SELF, Relationship.GUARDIAN})


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Registry then asks Access."""

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
        subject_person_id: UUID | None = None,
        relationship: Relationship | None = None,
    ) -> None:
        """Authorise a school-scoped library action."""
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id,
                subject_person_id=subject_person_id,
                relationship=relationship,
                effective_date=self.effective_date(),
            ),
        )

    def _allowed(self, context: RequestContext, action: str) -> bool:
        """Return True when Access would allow the school-scoped action."""
        decision = self.access.authorize(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id,
                effective_date=self.effective_date(),
            ),
        )
        return decision.allowed

    def require_borrower_visibility(
        self,
        context: RequestContext,
        person_id: UUID,
    ) -> None:
        """Allow staff circulate/overdue, or self/guardian for person_id.

        Student actors are never treated as staff, whatever their grants say.
        Unrelated actors get 404.
        """
        on = self.effective_date()
        actor_is_student = actor_kind(self.registry, context) == "student"
        if not actor_is_student and (
            self._allowed(context, "library.issue")
            or self._allowed(context, "library.read_overdues")
        ):
            return

        if person_id == context.actor_id:
            facts_rel = Relationship.SELF
        else:
            facts = self.registry.get_relationships(context, context.actor_id, person_id, on)
            facts_rel = facts.relationship
            if facts_rel not in OWN_RELATIONSHIPS:
                raise ObjectInaccessible("error.object_inaccessible")

        try:
            self.require_action(
                context,
                "library.read_own",
                subject_person_id=person_id,
                relationship=facts_rel,
            )
        except ActionDenied as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc

    def require_catalogue_read(self, context: RequestContext) -> None:
        """Allow catalogue manage/issue staff, or read_own for search/availability."""
        if self._allowed(context, "library.catalogue.manage") or self._allowed(
            context, "library.issue"
        ):
            return
        self.require_action(
            context,
            "library.read_own",
            relationship=Relationship.NONE,
        )

    def ensure_student_in_school(self, context: RequestContext, person_id: UUID) -> object:
        """Load student via Registry; other-school is inaccessible."""
        student = self.registry.get_student(context, person_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return student
