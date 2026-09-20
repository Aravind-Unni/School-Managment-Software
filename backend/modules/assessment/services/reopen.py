"""Reopen a published assessment; preserve old revision manifests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import StateConflict, ValidationFailed, VersionConflict
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..models import (
    Assessment,
    AssessmentState,
    Result,
    ResultRevision,
    ResultWorkflowStatus,
)
from .authority import AuthorityGate
from .wire import assessment_to_wire, build_result_snapshot


@dataclass(frozen=True, slots=True)
class ReopenService:
    """Reopen published results for correction."""

    gate: AuthorityGate
    platform: object
    clock: object

    def reopen(
        self,
        context: RequestContext,
        *,
        assessment_id: UUID,
        expected_version: int,
        reason: str | None,
    ) -> dict:
        """Move published → reopened. Old ResultRevision rows are retained.

        Emits assessment.result_revised per result with old and new revision ids.
        Requires a non-empty reason and recent 2FA.
        """
        if not reason or not str(reason).strip():
            raise ValidationFailed("assessment.error.reason_required")
        reason_text = str(reason).strip()

        assessment = self.gate.load_assessment(context, assessment_id)
        self.gate.require_publish_or_reopen(
            context, action="results.reopen", assessment=assessment
        )
        if assessment.state != AssessmentState.PUBLISHED:
            raise StateConflict("assessment.error.invalid_transition")
        if assessment.version != expected_version:
            raise VersionConflict("error.version_conflict")

        now = self.clock.now()
        with transaction.atomic():
            locked = Assessment.objects.select_for_update().get(id=assessment.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            if locked.state != AssessmentState.PUBLISHED:
                raise StateConflict("assessment.error.invalid_transition")

            for result in Result.objects.select_for_update().filter(assessment=locked):
                old_revision_id = result.current_revision_id
                if old_revision_id is None:
                    # Should not happen for published rows; keep a synthetic old id.
                    old_revision_id = uuid.uuid4()
                snapshot = build_result_snapshot(result, locked)
                # Working copy for edits: duplicate current evidence without revision.
                from ..models import EvidenceBinding

                published_bindings = list(
                    EvidenceBinding.objects.filter(
                        result=result, revision_id=result.current_revision_id
                    )
                )
                for binding in published_bindings:
                    EvidenceBinding.objects.create(
                        id=uuid.uuid4(),
                        result=result,
                        revision_id=None,
                        file_id=binding.file_id,
                        file_version=binding.file_version,
                        sha256=binding.sha256,
                        page_no=binding.page_no,
                    )

                new_revision = ResultRevision.objects.create(
                    id=uuid.uuid4(),
                    result=result,
                    school_id=locked.school_id,
                    snapshot=snapshot,
                    reason=reason_text,
                    created_at=now,
                )
                result.status = ResultWorkflowStatus.REOPENED
                result.current_revision_id = new_revision.id
                result.version += 1
                result.updated_at = now
                result.save(
                    update_fields=[
                        "status",
                        "current_revision_id",
                        "version",
                        "updated_at",
                    ]
                )
                self.platform.append_event(
                    EventEnvelope(
                        event_id=uuid.uuid4(),
                        school_id=context.school_id,
                        event_type="assessment.result_revised",
                        occurred_at=now,
                        aggregate_id=result.id,
                        aggregate_version=result.version,
                        payload={
                            "old_revision_id": str(old_revision_id),
                            "new_revision_id": str(new_revision.id),
                            "reason_code": "manual_correction",
                        },
                        correlation_id=context.request_id,
                    )
                )

            locked.state = AssessmentState.REOPENED
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["state", "version", "updated_at"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.reopened",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"reason": reason_text},
                )
            )

        return assessment_to_wire(
            Assessment.objects.prefetch_related("components").get(id=assessment_id)
        )
