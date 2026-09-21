"""Authority helpers for exchange reads, writes and artifact downloads.

Two distinct shapes live here on purpose:

  * ``require_staff_action`` — school-scoped bulk work with no single subject.
  * ``require_report_read``  — subject-scoped, relationship-resolved through
    Registry and re-checked at download time, so a link minted while a
    guardianship was live cannot be reissued after it lapses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID, uuid4

from contracts.errors import ActionDenied, ObjectInaccessible
from contracts.evidence import ResourceGrant
from contracts.identity import RequestContext
from contracts.scope import ScopeFacts
from contracts.values import school_date

from ..fixture_ids import NON_STAFF_ACTORS
from ..models import ExchangePolicy

#: Message key for a download refused because the relationship no longer reads.
ARTIFACT_ACCESS_REVOKED = "exchange.error.artifact_access_revoked"

#: Fallback signed-read lifetime when no ExchangePolicy row exists yet.
DEFAULT_SIGNED_READ_SECONDS = 120


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Resolves Access for school-scoped and subject-scoped exchange actions."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return the Asia/Kolkata civil date from the injected clock."""
        return school_date(self.clock.now())

    def policy(self, school_id: UUID) -> ExchangePolicy | None:
        """Return the school's fixture policy row, or None when unseeded."""
        return ExchangePolicy.objects.filter(school_id=school_id).first()

    def signed_read_seconds(self, school_id: UUID) -> int:
        """Return the signed-URL lifetime this school's fixture policy sets."""
        row = self.policy(school_id)
        return row.signed_read_seconds if row is not None else DEFAULT_SIGNED_READ_SECONDS

    def require_staff_action(self, context: RequestContext, action: str) -> None:
        """Authorise a school-scoped bulk action for a staff actor.

        Known non-staff fixture actors are refused before Access is consulted,
        so a guardian cannot reach a bulk endpoint even if a rule were declared
        too widely by mistake.
        """
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

    def require_commit(self, context: RequestContext) -> None:
        """Authorise imports.commit, demanding recent 2FA when the fixture says so."""
        self.require_staff_action(context, "imports.commit")
        row = self.policy(context.school_id)
        if row is not None and row.commit_requires_2fa:
            self.access.require_recent_2fa(context, max_age_seconds=300)

    def require_report_read(
        self,
        context: RequestContext,
        *,
        subject_person_id: UUID | None,
    ) -> None:
        """Authorise reports.read, relationship-gated for student-scoped reports.

        A snapshot with no subject (a whole-section roster, say) is school-scoped
        and skips the relationship lookup. A snapshot bound to one pupil asks
        Registry for the dated relationship and folds it into ScopeFacts, which
        is the only sanctioned way to populate it.

        Raises ActionDenied carrying ``exchange.error.artifact_access_revoked``
        so a caller can distinguish "you never could" from "you no longer can".
        """
        if subject_person_id is None:
            self.require_staff_action(context, "reports.read")
            return
        facts = self.registry.get_relationships(
            context,
            context.actor_id,
            subject_person_id,
            self.effective_date(),
        )
        if not facts.is_active_on(self.effective_date()):
            raise ActionDenied(ARTIFACT_ACCESS_REVOKED)
        scope = ScopeFacts.from_relationship(
            resource_school_id=context.school_id,
            facts=facts,
        )
        try:
            self.access.check(context, "reports.read", scope)
        except ActionDenied as denial:
            raise ActionDenied(ARTIFACT_ACCESS_REVOKED) from denial

    def mint_read_grant(self, context: RequestContext, resource_id: UUID) -> ResourceGrant:
        """Mint a short-lived server-internal grant for one artifact.

        Server-side only: the grant is built here from an Access decision just
        made, and is never read from a request body.
        """
        now = self.clock.now()
        return ResourceGrant(
            grant_id=uuid4(),
            school_id=context.school_id,
            actor_id=context.actor_id,
            action="reports.read",
            resource_id=resource_id,
            issued_at=now,
            expires_at=now + timedelta(seconds=self.signed_read_seconds(context.school_id)),
        )

    def ensure_student_in_school(self, context: RequestContext, student_id: UUID) -> object:
        """Load a student via Registry; an other-school pupil is 404, not 403."""
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return student
