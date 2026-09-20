"""Edit marks and marking outcomes on draft/reopened results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import (
    Assessment,
    AssessmentState,
    Mark,
    MarkingOutcome,
    Result,
    ResultWorkflowStatus,
)
from .authority import AuthorityGate
from .create import parse_mark
from .wire import format_mark, result_to_wire

EDITABLE_ASSESSMENT = frozenset({AssessmentState.DRAFT, AssessmentState.REOPENED})
NULL_SCORE_OUTCOMES = frozenset({MarkingOutcome.ABSENT, MarkingOutcome.EXEMPT})


@dataclass(frozen=True, slots=True)
class MarksService:
    """PATCH marks for one student result."""

    gate: AuthorityGate
    platform: object
    clock: object

    def patch(
        self,
        context: RequestContext,
        *,
        assessment_id: UUID,
        student_id: UUID,
        expected_version: int,
        attempt_id: UUID,
        status: str,
        marking_outcome: str | None = None,
        component_scores: list[dict] | None = None,
    ) -> dict:
        """Update marks on a draft or reopened result.

        Absent/exempt force score null. Score above component or assessment max
        is 422. Does not invent grade letters.
        """
        assessment = self.gate.load_assessment(context, assessment_id)
        if assessment.state not in EDITABLE_ASSESSMENT:
            raise StateConflict("assessment.error.invalid_transition")
        self.gate.require_assessment_action(context, action="marks.edit", assessment=assessment)

        if assessment.version != expected_version:
            raise VersionConflict("error.version_conflict")
        try:
            result = Result.objects.get(
                assessment=assessment, student_id=student_id, attempt_id=attempt_id
            )
        except Result.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc

        outcome = marking_outcome or result.marking_outcome
        if outcome not in {c.value for c in MarkingOutcome}:
            raise ValidationFailed("error.validation_failed")
        if status not in {c.value for c in ResultWorkflowStatus}:
            raise ValidationFailed("error.validation_failed")
        if status not in {
            ResultWorkflowStatus.DRAFT,
            ResultWorkflowStatus.REOPENED,
        }:
            raise ValidationFailed("error.validation_failed")

        component_by_id = {c.id: c for c in assessment.components.all()}
        scores_input = component_scores or []
        now = self.clock.now()

        with transaction.atomic():
            locked_assessment = Assessment.objects.select_for_update().get(id=assessment.id)
            if locked_assessment.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked_result = Result.objects.select_for_update().get(id=result.id)

            if outcome in NULL_SCORE_OUTCOMES:
                if scores_input:
                    for item in scores_input:
                        if parse_mark(item.get("score")) is not None:
                            raise ValidationFailed("assessment.error.absent_not_zero")
                locked_result.marks.all().delete()
                locked_result.score = None
                locked_result.marking_outcome = outcome
            else:
                total = Decimal("0")
                seen: set[UUID] = set()
                for item in scores_input:
                    component_id = item["component_id"]
                    if isinstance(component_id, str):
                        component_id = UUID(component_id)
                    component = component_by_id.get(component_id)
                    if component is None:
                        raise ValidationFailed("error.validation_failed")
                    score = parse_mark(item["score"])
                    if score is None:
                        raise ValidationFailed("error.validation_failed")
                    if score > component.max_score:
                        raise ValidationFailed("assessment.error.score_above_max")
                    seen.add(component_id)
                    Mark.objects.update_or_create(
                        result=locked_result,
                        component_id=component_id,
                        defaults={"score": score},
                    )
                    total += score
                if total > locked_assessment.max_score:
                    raise ValidationFailed("assessment.error.score_above_max")
                if scores_input:
                    locked_result.score = total
                locked_result.marking_outcome = outcome

            locked_result.status = status
            locked_result.version += 1
            locked_result.updated_at = now
            locked_result.save(
                update_fields=[
                    "status",
                    "marking_outcome",
                    "score",
                    "version",
                    "updated_at",
                ]
            )
            if locked_assessment.marks_author_id is None:
                locked_assessment.marks_author_id = context.actor_id
            locked_assessment.version += 1
            locked_assessment.updated_at = now
            locked_assessment.save(update_fields=["marks_author_id", "version", "updated_at"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.marks_patched",
                    resource_id=locked_result.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={
                        "marking_outcome": locked_result.marking_outcome,
                        "score": format_mark(locked_result.score),
                    },
                )
            )

        refreshed = Result.objects.prefetch_related("marks", "evidence_bindings").get(
            id=result.id
        )
        refreshed_assessment = Assessment.objects.prefetch_related("components").get(
            id=assessment.id
        )
        return {
            "result": result_to_wire(refreshed, assessment=refreshed_assessment),
            "version": refreshed_assessment.version,
            "total": format_mark(refreshed.score),
        }
