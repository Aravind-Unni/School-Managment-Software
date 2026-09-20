"""Create assessment structures and roster result shells."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.db import transaction

from contracts.errors import ValidationFailed
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import (
    Assessment,
    AssessmentState,
    AssessmentType,
    Component,
    MarkingOutcome,
    Result,
    ResultWorkflowStatus,
)
from .authority import AuthorityGate
from .wire import assessment_to_wire

WEIGHT_TOLERANCE = Decimal("0.001")


def parse_mark(raw: str | None) -> Decimal | None:
    """Parse a contracted decimal-string mark.

    Does not handle: locale-specific separators.
    """
    if raw is None:
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError) as exc:
        raise ValidationFailed("error.validation_failed") from exc
    if value < 0:
        raise ValidationFailed("error.validation_failed")
    return value


def validate_component_weights(components: list[dict]) -> Decimal:
    """Require component weights to sum to 1.000 within tolerance."""
    total = Decimal("0")
    for item in components:
        weight = parse_mark(item["weight"])
        if weight is None:
            raise ValidationFailed("assessment.error.weight_total_invalid")
        total += weight
    if abs(total - Decimal("1")) > WEIGHT_TOLERANCE:
        raise ValidationFailed("assessment.error.weight_total_invalid")
    return total


@dataclass(frozen=True, slots=True)
class CreateService:
    """Create draft assessments with components and empty results."""

    gate: AuthorityGate
    registry: object
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        year_id: UUID,
        term_id: UUID,
        section_id: UUID,
        subject_id: UUID,
        assessment_type: str,
        components: list[dict],
        policy_version: str,
        due_at=None,
        max_score: str | None = None,
        assessment_id: UUID | None = None,
        result_ids: dict[UUID, UUID] | None = None,
        attempt_ids: dict[UUID, UUID] | None = None,
    ) -> dict:
        """Create a draft assessment for the roster of section+subject.

        Optional fixed ids support the baseline seed. Does not invent grade
        boundaries. Assignment type requires due_at.
        """
        if assessment_type not in {c.value for c in AssessmentType}:
            raise ValidationFailed("error.validation_failed")
        if assessment_type == AssessmentType.ASSIGNMENT and due_at is None:
            raise ValidationFailed("assessment.error.due_at_required")
        if not components:
            raise ValidationFailed("error.validation_failed")
        if not policy_version:
            raise ValidationFailed("error.validation_failed")

        validate_component_weights(components)
        self.gate.require_section_subject_action(
            context,
            action="assessment.manage",
            section_id=section_id,
            subject_id=subject_id,
        )

        component_maxes = [parse_mark(c["max_score"]) for c in components]
        if any(m is None for m in component_maxes):
            raise ValidationFailed("error.validation_failed")
        computed_max = sum(component_maxes, Decimal("0"))
        if max_score is not None:
            override = parse_mark(max_score)
            if override is None:
                raise ValidationFailed("error.validation_failed")
            total_max = override
        else:
            total_max = computed_max

        on = self.gate.effective_date()
        roster = self.registry.get_roster(context, section_id, on, subject_id=subject_id)
        now = self.clock.now()
        new_id = assessment_id or uuid.uuid4()

        with transaction.atomic():
            assessment = Assessment.objects.create(
                id=new_id,
                school_id=context.school_id,
                year_id=year_id,
                term_id=term_id,
                section_id=section_id,
                subject_id=subject_id,
                type=assessment_type,
                max_score=total_max,
                policy_version=policy_version,
                state=AssessmentState.DRAFT,
                version=1,
                due_at=due_at,
                created_at=now,
                updated_at=now,
            )
            for index, item in enumerate(components):
                component_id = item.get("id") or uuid.uuid4()
                if isinstance(component_id, str):
                    component_id = UUID(component_id)
                Component.objects.create(
                    id=component_id,
                    assessment=assessment,
                    max_score=parse_mark(item["max_score"]),
                    weight=parse_mark(item["weight"]),
                    topic=item.get("topic"),
                    question_type=item.get("question_type"),
                    sort_order=index,
                )
            for row in roster.students:
                Result.objects.create(
                    id=(result_ids or {}).get(row.student_id, uuid.uuid4()),
                    assessment=assessment,
                    school_id=context.school_id,
                    student_id=row.student_id,
                    attempt_id=(attempt_ids or {}).get(row.student_id, uuid.uuid4()),
                    status=ResultWorkflowStatus.DRAFT,
                    marking_outcome=MarkingOutcome.SCORED,
                    score=None,
                    version=1,
                    updated_at=now,
                )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.created",
                    resource_id=assessment.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"type": assessment_type, "policy_version": policy_version},
                )
            )
        return assessment_to_wire(
            Assessment.objects.prefetch_related("components").get(id=assessment.id)
        )
