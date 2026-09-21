"""Publish approved assessments with idempotency and report enqueue."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError, transaction

from contracts.errors import StateConflict, ValidationFailed, VersionConflict
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..models import (
    Assessment,
    AssessmentState,
    EvidenceBinding,
    Publication,
    PublishIdempotency,
    Result,
    ResultRevision,
    ResultWorkflowStatus,
)
from .authority import AuthorityGate
from .wire import build_result_snapshot, publication_to_wire
from .workflow import assert_evidence_confirmed, assert_marks_complete, evidence_required


@dataclass(frozen=True, slots=True)
class PublishService:
    """Publish approved results as one idempotent batch."""

    gate: AuthorityGate
    files: object
    platform: object
    clock: object

    def publish(
        self,
        context: RequestContext,
        *,
        assessment_id: UUID,
        expected_version: int,
        idempotency_key: str,
    ) -> dict:
        """Publish approved results. Same Idempotency-Key retries return the batch.

        Emits assessment.results_published once. Enqueues assessment.report_snapshot
        after the write commits when a worker is available.
        """
        if not idempotency_key:
            raise ValidationFailed("assessment.error.idempotency_key_required")

        existing = PublishIdempotency.objects.filter(
            school_id=context.school_id,
            assessment_id=assessment_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            publication = Publication.objects.get(id=existing.publication_id)
            return publication_to_wire(
                publication.id,
                publication.result_revision_ids,
                publication.report_job_id,
            )

        assessment = self.gate.load_assessment(context, assessment_id)
        self.gate.require_publish_or_reopen(
            context, action="results.publish", assessment=assessment
        )
        if assessment.state == AssessmentState.PUBLISHED:
            raise StateConflict("assessment.error.already_published")
        if assessment.state != AssessmentState.APPROVED:
            raise StateConflict("assessment.error.invalid_transition")
        if assessment.version != expected_version:
            raise VersionConflict("error.version_conflict")

        assert_marks_complete(
            assessment, require_evidence=evidence_required(self.gate.registry, context)
        )
        assert_evidence_confirmed(assessment, self.files, context)

        now = self.clock.now()
        publication_id = uuid.uuid4()
        revision_ids: list[str] = []

        with transaction.atomic():
            locked = Assessment.objects.select_for_update().get(id=assessment.id)
            if locked.version != expected_version:
                raise VersionConflict("error.version_conflict")
            if locked.state == AssessmentState.PUBLISHED:
                raise StateConflict("assessment.error.already_published")

            for result in Result.objects.select_for_update().filter(assessment=locked):
                snapshot = build_result_snapshot(result, locked)
                revision = ResultRevision.objects.create(
                    id=uuid.uuid4(),
                    result=result,
                    school_id=locked.school_id,
                    snapshot=snapshot,
                    reason="",
                    created_at=now,
                )
                revision_ids.append(str(revision.id))
                # Pin working evidence onto this revision; leave rows for readers.
                EvidenceBinding.objects.filter(result=result, revision_id__isnull=True).update(
                    revision_id=revision.id
                )
                result.status = ResultWorkflowStatus.PUBLISHED
                result.current_revision_id = revision.id
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

            locked.state = AssessmentState.PUBLISHED
            locked.version += 1
            locked.updated_at = now
            locked.save(update_fields=["state", "version", "updated_at"])

            report_job_id = self._enqueue_report(
                context,
                assessment_id=locked.id,
                publication_id=publication_id,
            )
            Publication.objects.create(
                id=publication_id,
                assessment=locked,
                school_id=locked.school_id,
                result_revision_ids=revision_ids,
                actor_id=context.actor_id,
                published_at=now,
                report_job_id=report_job_id,
            )
            try:
                PublishIdempotency.objects.create(
                    id=uuid.uuid4(),
                    school_id=context.school_id,
                    assessment_id=locked.id,
                    idempotency_key=idempotency_key,
                    publication_id=publication_id,
                    created_at=now,
                )
            except IntegrityError:
                pass

            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="assessment.published",
                    resource_id=locked.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"publication_id": str(publication_id)},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="assessment.results_published",
                    occurred_at=now,
                    aggregate_id=locked.id,
                    aggregate_version=locked.version,
                    payload={
                        "assessment_id": str(locked.id),
                        "publication_id": str(publication_id),
                        "result_revision_ids": revision_ids,
                    },
                    correlation_id=context.request_id,
                )
            )

        publication = Publication.objects.get(id=publication_id)
        return publication_to_wire(
            publication.id,
            publication.result_revision_ids,
            publication.report_job_id,
        )

    def _enqueue_report(
        self,
        context: RequestContext,
        *,
        assessment_id: UUID,
        publication_id: UUID,
    ) -> str:
        """Enqueue the report snapshot job, or defer when no worker is bound.

        Does not claim crash/retry coverage when the adapter refuses enqueue.
        """
        if not getattr(self.platform, "worker_available", True):
            return f"deferred-no-worker:{publication_id}"
        return self.platform.enqueue(
            "assessment.report_snapshot",
            payload={
                "assessment_id": str(assessment_id),
                "publication_id": str(publication_id),
                "request_id": context.request_id,
            },
        )
