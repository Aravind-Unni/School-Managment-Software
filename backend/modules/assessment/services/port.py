"""In-process AssessmentPort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.identity import RequestContext
from contracts.scope import Relationship, ScopeFacts
from shared.people import is_school_wide_reader

from ..models import (
    Assessment,
    AssessmentState,
    AssessmentType,
    Result,
    ResultRevision,
    ResultWorkflowStatus,
)
from .authority import READING_RELATIONSHIPS, AuthorityGate
from .wire import result_to_wire, revision_snapshot_result


@dataclass(frozen=True, slots=True)
class AssessmentService:
    """Published assessment facts another module consumes in-process."""

    gate: AuthorityGate
    access: object
    registry: object
    clock: object

    def get_published_results(
        self,
        context: RequestContext,
        student_id: UUID,
        term_id: UUID,
        cursor: str | None = None,
    ) -> dict[str, object]:
        """Return published results for one pupil in one term.

        Draft/submitted/approved rows are never returned to student or guardian
        scopes. Staff with a reading relationship see published rows only.
        """
        del cursor  # cursor pagination reserved; baseline returns a single page
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        on = self.gate.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.relationship not in READING_RELATIONSHIPS and not is_school_wide_reader(
            self.access, context, on
        ):
            raise ObjectInaccessible("error.object_inaccessible")
        self.access.check(
            context,
            "evidence.view",
            ScopeFacts(
                resource_school_id=context.school_id,
                subject_person_id=student_id,
                relationship=facts.relationship,
                effective_date=on,
            ),
        )

        results = (
            Result.objects.select_related("assessment")
            .prefetch_related("evidence_bindings", "marks")
            .filter(
                school_id=context.school_id,
                student_id=student_id,
                assessment__term_id=term_id,
                status=ResultWorkflowStatus.PUBLISHED,
            )
            .order_by("id")
        )
        items = []
        for result in results:
            assessment = result.assessment
            if assessment.state != AssessmentState.PUBLISHED:
                continue
            if facts.relationship in {Relationship.SELF, Relationship.GUARDIAN}:
                if result.status != ResultWorkflowStatus.PUBLISHED:
                    continue
            bindings = list(
                result.evidence_bindings.filter(revision_id=result.current_revision_id)
            )
            items.append(
                result_to_wire(
                    result,
                    assessment=assessment,
                    revision_id=result.current_revision_id,
                    evidence=bindings,
                )
            )
        return {"items": items, "next_cursor": None}

    def get_assignment_summary(
        self,
        context: RequestContext,
        student_id: UUID,
        window_from: datetime,
        window_to: datetime,
    ) -> dict[str, object]:
        """Return assignment counts for one pupil in a closed time window.

        Only assessments with type=assignment. Draft data never leaks to
        student/guardian: missing means not submitted by due_at.
        """
        if window_to < window_from:
            raise ValidationFailed("error.validation_failed")
        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        on = self.gate.effective_date()
        facts = self.registry.get_relationships(context, context.actor_id, student_id, on)
        if facts.relationship not in READING_RELATIONSHIPS and not is_school_wide_reader(
            self.access, context, on
        ):
            raise ObjectInaccessible("error.object_inaccessible")
        self.access.check(
            context,
            "evidence.view",
            ScopeFacts(
                resource_school_id=context.school_id,
                subject_person_id=student_id,
                relationship=facts.relationship,
                effective_date=on,
            ),
        )

        assessments = Assessment.objects.filter(
            school_id=context.school_id,
            type=AssessmentType.ASSIGNMENT,
            due_at__gte=window_from,
            due_at__lte=window_to,
        )
        assigned = assessments.count()
        due = assessments.filter(due_at__lte=self.clock.now()).count()
        results = Result.objects.filter(
            student_id=student_id,
            assessment__in=assessments,
            status__in={
                ResultWorkflowStatus.SUBMITTED,
                ResultWorkflowStatus.APPROVED,
                ResultWorkflowStatus.PUBLISHED,
            },
        )
        submitted = results.count()
        missing = max(due - submitted, 0)
        return {
            "assigned": assigned,
            "due": due,
            "submitted": submitted,
            "missing": missing,
            "updated_at": self.clock.now().isoformat(),
        }

    def get_revision(self, context: RequestContext, revision_id: UUID) -> ResultRevision | None:
        """Load a school-scoped revision for retention assertions."""
        try:
            revision = ResultRevision.objects.select_related("result__assessment").get(
                id=revision_id
            )
        except ResultRevision.DoesNotExist:
            return None
        if revision.school_id != context.school_id:
            return None
        return revision

    def published_result_from_revision(self, revision: ResultRevision) -> dict[str, object]:
        """Rebuild a published ResultDTO from a retained revision snapshot."""
        return revision_snapshot_result(revision, revision.result.assessment)
