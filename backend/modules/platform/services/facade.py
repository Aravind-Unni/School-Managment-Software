"""Ergonomic facades matching Development Manual wording."""

from __future__ import annotations

from uuid import UUID, uuid4

from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext

from ..fixture_ids import JOB_KINDS_ALLOWLIST
from .adapter import PlatformAdapter


class PlatformFacade:
    """Wrap PlatformAdapter with ctx-first helpers used by domain callers."""

    def __init__(self, *, platform: PlatformAdapter, clock) -> None:
        """Bind adapter and clock."""
        self._platform = platform
        self._clock = clock

    def record_audit(
        self,
        ctx: RequestContext,
        action: str,
        aggregate_id: UUID,
        redacted_diff: dict,
    ) -> UUID:
        """Append audit and return audit_id."""
        audit_id = uuid4()
        before = dict(redacted_diff.get("before") or {})
        after = dict(redacted_diff.get("after") or {})
        self._platform.record_audit(
            AuditRecord(
                audit_id=audit_id,
                school_id=ctx.school_id,
                actor_id=ctx.actor_id,
                action=action,
                resource_id=aggregate_id,
                occurred_at=self._clock.now(),
                request_id=ctx.request_id,
                before=before,
                after=after,
            )
        )
        return audit_id

    def append_event(
        self,
        ctx: RequestContext,
        event_type: str,
        aggregate_id: UUID,
        aggregate_version: int,
        payload: dict,
    ) -> UUID:
        """Append outbox event and return event_id."""
        event_id = uuid4()
        self._platform.append_event(
            EventEnvelope(
                event_id=event_id,
                school_id=ctx.school_id,
                event_type=event_type,
                occurred_at=self._clock.now(),
                aggregate_id=aggregate_id,
                aggregate_version=aggregate_version,
                payload=payload,
                correlation_id=ctx.request_id,
            )
        )
        return event_id

    def start_job(
        self,
        ctx: RequestContext,
        kind: str,
        idempotency_key: str,
        payload_ref: str,
    ) -> dict:
        """Create a job via enqueue and return {job_id, state}."""
        from contracts.errors import ValidationFailed

        from ..models import Job

        if kind not in JOB_KINDS_ALLOWLIST:
            raise ValidationFailed("platform.error.unknown_job_kind")
        job_id = self._platform.enqueue(
            kind,
            payload={
                "kind": kind,
                "school_id": str(ctx.school_id),
                "actor_id": str(ctx.actor_id),
                "idempotency_key": idempotency_key,
                "payload_ref": payload_ref,
            },
        )
        row = Job.objects.get(id=job_id)
        return {"job_id": str(row.id), "state": row.state}
