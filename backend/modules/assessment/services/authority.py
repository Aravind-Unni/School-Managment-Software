"""Teaching-assignment gate and Access checks for assessment writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ActionDenied, ObjectInaccessible
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from shared.people import is_school_wide_reader

from ..models import Assessment

PUBLISH_TWO_FACTOR_MAX_AGE_SECONDS = 300

READING_RELATIONSHIPS = frozenset(
    {
        Relationship.SELF,
        Relationship.GUARDIAN,
        Relationship.ASSIGNED_TEACHER,
        Relationship.CLASS_TEACHER,
    }
)


#: Review actions a school-wide grant holder may take on any class's results;
#: everyone else needs the section/subject teaching assignment.
SCHOOL_REVIEW_ACTIONS = frozenset({"results.approve", "results.publish", "results.reopen"})


@dataclass(frozen=True, slots=True)
class AuthorityGate:
    """Combines Registry teaching assignments with Access policy."""

    access: object
    registry: object
    clock: object

    def effective_date(self) -> date:
        """Return the school civil date for assignment checks.

        Assumes SCHOOL_CLOCK is timezone-aware. Does not invent term calendars.
        """
        from contracts.values import school_date

        return school_date(self.clock.now())

    def require_section_subject_action(
        self,
        context: RequestContext,
        *,
        action: str,
        section_id: UUID,
        subject_id: UUID,
        resource_school_id: UUID | None = None,
    ) -> None:
        """Authorise a teacher write for one section+subject.

        Requires Access permission AND that get_teaching_assignments includes the
        section and subject for the actor on the effective date.
        """
        school_id = resource_school_id or context.school_id
        on = self.effective_date()
        assignments = self.registry.get_teaching_assignments(context, context.actor_id, on)
        authorised = any(
            row.section_id == section_id and row.subject_id == subject_id for row in assignments
        )
        if not authorised:
            raise ActionDenied("error.action_denied")
        self.access.check(
            context,
            action,
            ScopeFacts(
                resource_school_id=school_id,
                section_id=section_id,
                subject_id=subject_id,
                effective_date=on,
            ),
        )

    def require_assessment_action(
        self,
        context: RequestContext,
        *,
        action: str,
        assessment: Assessment,
        require_assignment: bool = True,
    ) -> None:
        """Authorise an action against an existing assessment.

        Cross-school assessments are ObjectInaccessible (404), never 403.
        """
        if assessment.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if action in SCHOOL_REVIEW_ACTIONS and self._holds_school_wide(context, action):
            # A principal or academic head reviews every class's results
            # without being its subject teacher.
            return
        if require_assignment:
            self.require_section_subject_action(
                context,
                action=action,
                section_id=assessment.section_id,
                subject_id=assessment.subject_id,
                resource_school_id=assessment.school_id,
            )
        else:
            self.access.check(
                context,
                action,
                ScopeFacts(resource_school_id=assessment.school_id),
            )

    def _holds_school_wide(self, context: RequestContext, action: str) -> bool:
        """Return whether Access grants ``action`` across the whole school."""
        return self.access.authorize(
            context,
            action,
            ScopeFacts(
                resource_school_id=context.school_id, effective_date=self.effective_date()
            ),
        ).allowed

    def require_publish_or_reopen(
        self,
        context: RequestContext,
        *,
        action: str,
        assessment: Assessment,
    ) -> None:
        """Authorise publish/reopen with recent 2FA and section assignment."""
        self.access.require_recent_2fa(
            context, max_age_seconds=PUBLISH_TWO_FACTOR_MAX_AGE_SECONDS
        )
        self.require_assessment_action(
            context, action=action, assessment=assessment, require_assignment=True
        )

    def require_evidence_view(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        school_id: UUID,
    ) -> Relationship:
        """Authorise viewing pinned evidence for one pupil.

        Uses Registry relationships; Access evidence.view is relationship-gated.
        Returns the resolved relationship for callers that need it.
        """
        if school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        on = self.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.relationship not in READING_RELATIONSHIPS and not is_school_wide_reader(
            self.access, context, on
        ):
            raise ObjectInaccessible("error.object_inaccessible")
        self.access.check(
            context,
            "evidence.view",
            ScopeFacts(
                resource_school_id=school_id,
                subject_person_id=student_id,
                relationship=facts.relationship,
                effective_date=on,
            ),
        )
        return facts.relationship

    def load_assessment(self, context: RequestContext, assessment_id: UUID) -> Assessment:
        """Load a school-scoped assessment or raise 404."""
        try:
            assessment = Assessment.objects.prefetch_related("components").get(id=assessment_id)
        except Assessment.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if assessment.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return assessment
