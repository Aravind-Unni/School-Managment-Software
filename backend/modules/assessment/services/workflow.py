"""Submit and approve assessment batches."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import StateConflict, ValidationFailed, VersionConflict
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import (
    Approval,
    Assessment,
    AssessmentState,
    AssessmentType,
    MarkingOutcome,
    Result,
    ResultWorkflowStatus,
)
from .authority import AuthorityGate
from .wire import assessment_to_wire


def evidence_required(registry, context) -> bool:
    """Return whether scored written tests need a scanned answer sheet.

    The school decides, in its config file (``written_test_requires_evidence``);
    with no configured school the stricter rule applies.
    """
    profile = registry.school_profile(context) if registry is not None else None
    if profile is None:
        return True
    return bool(profile.settings.get("written_test_requires_evidence", True))


def assert_marks_complete(assessment: Assessment, *, require_evidence: bool = True) -> None:
    """Raise when scored results lack complete component scores or evidence.

    ``require_evidence`` applies the school's written-test scan rule.
    Does not handle: oral/practical evidence rules beyond scored written work.
    """
    component_ids = {c.id for c in assessment.components.all()}
    for result in assessment.results.all():
        if result.marking_outcome in {
            MarkingOutcome.ABSENT,
            MarkingOutcome.EXEMPT,
        }:
            if result.score is not None:
                raise ValidationFailed("assessment.error.absent_not_zero")
            continue
        if result.marking_outcome != MarkingOutcome.SCORED:
            continue
        marked = {m.component_id for m in result.marks.all()}
        if marked != component_ids:
            raise ValidationFailed("assessment.error.incomplete_marks")
        if require_evidence and assessment.type == AssessmentType.WRITTEN_TEST:
            evidence = result.evidence_bindings.filter(revision_id__isnull=True)
            if not evidence.exists():
                raise ValidationFailed("assessment.error.evidence_required")
            # Unconfirmed is checked at bind time and again at publish.


def assert_evidence_confirmed(assessment: Assessment, files, context) -> None:
    """Raise unconfirmed_evidence when any bound file is not quality-confirmed."""
    for result in assessment.results.all():
        if result.marking_outcome != MarkingOutcome.SCORED:
            continue
        for binding in result.evidence_bindings.filter(revision_id__isnull=True):
            dto = files.get_status(context, binding.file_id)
            if not dto.review_confirmed or dto.canonical_version != binding.file_version:
                raise ValidationFailed("assessment.error.unconfirmed_evidence")


@dataclass(frozen=True, slots=True)
class WorkflowService:
    """Submit for review and approve submitted batches."""

    gate: AuthorityGate
    platform: object
    clock: object

    def submit(
        self,
        context: RequestContext,
        *,
        assessment_id: UUID,
        expected_version: int,
    ) -> dict:
        """Transition draft/reopened → submitted after completeness checks."""
        assessment = self.gate.load_assessment(context, assessment_id)
        self.gate.require_assessment_action(
            context, action="marks.submit", assessment=assessment
        )
        if assessment.state not in {
            AssessmentState.DRAFT,
            AssessmentState.REOPENED,
        }:
            raise StateConflict("assessment.error.invalid_transition")
        if assessment.version != expected_version:
            raise VersionConflict("error.version_conflict")

        assert_marks_complete(
            assessment, require_evidence=evidence_required(self.gate.registry, context)
        )

        now = self.clock.now()
        with transaction.atomic():
            locked = Assessment.objects.select_for_update().get(id=assessment.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked.state = AssessmentState.SUBMITTED
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["state", "version", "updated_at"])
            Result.objects.filter(assessment=locked).update(
                status=ResultWorkflowStatus.SUBMITTED, updated_at=now
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.submitted",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"version": locked.version},
                )
            )
        return assessment_to_wire(
            Assessment.objects.prefetch_related("components").get(id=assessment_id)
        )

    def approve(
        self,
        context: RequestContext,
        *,
        assessment_id: UUID,
        expected_version: int,
    ) -> dict:
        """Transition submitted → approved."""
        assessment = self.gate.load_assessment(context, assessment_id)
        self.gate.require_assessment_action(
            context, action="results.approve", assessment=assessment
        )
        if assessment.state != AssessmentState.SUBMITTED:
            raise StateConflict("assessment.error.invalid_transition")
        if assessment.version != expected_version:
            raise VersionConflict("error.version_conflict")
        if (
            assessment.require_distinct_approver
            and assessment.marks_author_id == context.actor_id
        ):
            raise ValidationFailed("assessment.error.distinct_approver_required")

        assert_marks_complete(
            assessment, require_evidence=evidence_required(self.gate.registry, context)
        )

        now = self.clock.now()
        with transaction.atomic():
            locked = Assessment.objects.select_for_update().get(id=assessment.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            locked.state = AssessmentState.APPROVED
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["state", "version", "updated_at"])
            Result.objects.filter(assessment=locked).update(
                status=ResultWorkflowStatus.APPROVED, updated_at=now
            )
            Approval.objects.create(
                id=uuid.uuid4(),
                assessment=locked,
                actor_id=context.actor_id,
                approved_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.approved",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"version": locked.version},
                )
            )
        return assessment_to_wire(
            Assessment.objects.prefetch_related("components").get(id=assessment_id)
        )
