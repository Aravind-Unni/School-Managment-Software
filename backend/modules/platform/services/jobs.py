"""Job read and retry services."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import Job, JobState
from .authority import AuthorityGate
from .wire import job_dto


@dataclass(frozen=True, slots=True)
class JobService:
    """Scoped job progress and safe retry."""

    gate: AuthorityGate
    platform: object
    clock: object

    def get(self, context: RequestContext, job_id: UUID) -> dict:
        """Return JobDTO for a same-school job."""
        self.gate.require_action(context, "jobs.read")
        row = Job.objects.filter(id=job_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self.gate.same_school_or_404(context, row.school_id)
        return job_dto(row)

    def retry(self, context: RequestContext, job_id: UUID, *, reason: str) -> dict:
        """Replay a failed or dead job preserving idempotency_key."""
        self.gate.require_action(context, "jobs.retry")
        if not reason or len(reason) > 500:
            raise ValidationFailed("error.validation_failed")
        row = Job.objects.filter(id=job_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        self.gate.same_school_or_404(context, row.school_id)
        if row.state not in {JobState.FAILED, JobState.DEAD}:
            raise StateConflict("platform.error.job_not_retryable")
        now = self.clock.now()
        from_state = row.state
        row.state = JobState.QUEUED
        row.progress = 0
        row.error_code = None
        row.version += 1
        row.updated_at = now
        row.save(update_fields=["state", "progress", "error_code", "version", "updated_at"])
        from .job_runner import dispatch_after_commit, resolve_handler

        if resolve_handler(row.task_path) is not None:
            dispatch_after_commit(row.id)
        self.platform.record_audit(
            AuditRecord(
                audit_id=uuid4(),
                school_id=context.school_id,
                actor_id=context.actor_id,
                action="platform.job_retried",
                resource_id=row.id,
                occurred_at=now,
                request_id=context.request_id,
                before={"state": from_state},
                after={"state": row.state, "reason": reason},
            )
        )
        return job_dto(row)
