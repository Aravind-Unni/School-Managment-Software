"""Real PlatformPort adapter. Bound for M14; never used as a silent FakePlatform.

Writes join the caller's open transaction — no nested atomic here.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from django.conf import settings

from contracts.events import AuditRecord, EventEnvelope

from ..fixture_ids import JOB_KINDS_ALLOWLIST
from ..models import AuditRecord as AuditRow
from ..models import Job, JobState, OutboxEvent, OutboxState
from .redaction import redact_mapping

#: Actor recorded on jobs whose producer carried none (system work).
SYSTEM_ACTOR_ID = UUID("00000000-0000-5000-8000-000000000001")


@dataclass
class PlatformAdapter:
    """Production-shaped PlatformPort writing to platform_* tables.

    ``worker_available`` gates enqueue the same way TestPlatformAdapter does, so
    suites cannot claim crash/retry coverage without a real broker.
    """

    worker_available: bool = False
    clock: object | None = None

    def record_audit(self, record: AuditRecord) -> None:
        """Insert one audit row using the caller's open transaction."""
        AuditRow.objects.create(
            id=record.audit_id,
            school_id=record.school_id,
            actor_id=record.actor_id,
            action=record.action,
            resource_id=record.resource_id,
            occurred_at=record.occurred_at,
            request_id=record.request_id,
            before=redact_mapping(dict(record.before)),
            after=redact_mapping(dict(record.after)),
        )

    def append_event(self, event: EventEnvelope) -> None:
        """Insert one pending outbox row using the caller's open transaction."""
        OutboxEvent.objects.create(
            event_id=event.event_id,
            school_id=event.school_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            aggregate_id=event.aggregate_id,
            aggregate_version=event.aggregate_version,
            payload=dict(event.payload),
            envelope_version=event.envelope_version,
            correlation_id=event.correlation_id,
            state=OutboxState.PENDING,
            attempts=0,
        )

    def enqueue(self, task_path: str, *, payload: dict[str, object]) -> str:
        """Create or reuse a Job and return its id.

        Raises EagerModeNotAsserted when no real worker is available, matching
        the harness adapter so async claims stay honest.
        """
        from shared.fakes.platform import EagerModeNotAsserted

        if not self.worker_available:
            raise EagerModeNotAsserted(
                f"enqueue({task_path!r}) requires a real broker and worker; "
                "this profile has none, so asynchronous behaviour cannot be asserted."
            )
        kind = str(payload.get("kind") or task_path)
        if kind not in JOB_KINDS_ALLOWLIST and not kind.startswith("platform."):
            kind = task_path if task_path.startswith("platform.") else f"platform.{kind}"
        # Not every producer carries identity in its payload (file processing,
        # deliveries); the deployment's school and a system actor stand in.
        school_id = UUID(str(payload.get("school_id") or settings.SCHOOL_ID))
        actor_id = UUID(str(payload.get("actor_id") or SYSTEM_ACTOR_ID))
        idempotency_key = str(payload.get("idempotency_key") or uuid4())
        payload_ref = str(payload.get("payload_ref") or f"payloads/{idempotency_key}")
        now = self._now()
        existing = Job.objects.filter(
            school_id=school_id, kind=kind, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            return str(existing.id)
        job = Job.objects.create(
            id=uuid4(),
            school_id=school_id,
            actor_id=actor_id,
            kind=kind,
            payload_ref=payload_ref,
            task_path=task_path,
            payload=dict(payload),
            state=JobState.QUEUED,
            progress=0,
            error_code=None,
            idempotency_key=idempotency_key,
            version=1,
            created_at=now,
            updated_at=now,
        )
        from .job_runner import dispatch_after_commit, resolve_handler

        if resolve_handler(task_path) is not None:
            dispatch_after_commit(job.id)
        return str(job.id)

    def audit_rows(self, *, school_id: UUID | None = None) -> list[dict[str, object]]:
        """Return visible audit rows for rollback assertions."""
        queryset = AuditRow.objects.all()
        if school_id is not None:
            queryset = queryset.filter(school_id=school_id)
        return list(queryset.values())

    def outbox_rows(self, *, school_id: UUID | None = None) -> list[dict[str, object]]:
        """Return visible outbox rows for rollback assertions."""
        queryset = OutboxEvent.objects.all()
        if school_id is not None:
            queryset = queryset.filter(school_id=school_id)
        return list(queryset.values())

    @property
    def supports_worker_assertions(self) -> bool:
        """Return whether this profile can honestly assert async behaviour."""
        return self.worker_available

    def _now(self):
        """Return clock.now() or fail when no clock was injected."""
        if self.clock is None:
            from django.utils import timezone

            return timezone.now()
        return self.clock.now()
