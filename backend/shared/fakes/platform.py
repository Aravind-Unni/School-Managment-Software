"""Platform TEST adapter: audit + outbox into harness-owned tables.

This is a test implementation sharing a behavioural contract with M14's real
Platform, not a production replacement. It is bound for every module except M14;
M14 binds its actual implementation.

Two properties matter and are asserted by tests/contracts:
  1. ``record_audit`` and ``append_event`` join the CALLER's transaction. No
     ``transaction.atomic()`` is opened here, so a rollback in the caller
     removes the rows.
  2. ``enqueue`` refuses to pretend. In eager-only mode it raises rather than
     returning a job id, so no suite can claim worker crash/retry coverage it
     did not earn.

Does not handle: relaying committed outbox rows to the broker. A real relay is
M14's job; standalone tests assert the row, not its delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.events import AuditRecord, EventEnvelope

from .failures import FailureInjector


class EagerModeNotAsserted(RuntimeError):
    """Raised when async behaviour is exercised without a real worker.

    B00 forbids claiming worker crash/retry results from eager execution. Rather
    than silently running the task inline, the adapter raises so the test is
    marked as requiring a broker.
    """


@dataclass(frozen=True, slots=True)
class EnqueuedJob:
    """One job the adapter recorded instead of dispatching."""

    job_id: str
    task_path: str
    payload: dict[str, object]


class TestPlatformAdapter:
    """PlatformPort implementation writing to harness tables.

    Constructed with ``worker_available`` reflecting whether a real broker and
    worker are running for this profile. When False, ``enqueue`` raises
    EagerModeNotAsserted.
    """

    def __init__(
        self,
        *,
        worker_available: bool = False,
        failures: FailureInjector | None = None,
    ) -> None:
        """Build the adapter.

        ``worker_available`` must be supplied by the harness from the real
        Compose state, never defaulted to True, so the honest failure is the
        default behaviour.
        """
        self._worker_available = worker_available
        self._failures = failures or FailureInjector()
        self.enqueued: list[EnqueuedJob] = []

    # --- writes that must share the caller's transaction ------------------

    def record_audit(self, record: AuditRecord) -> None:
        """Insert one audit row using the caller's open transaction.

        Deliberately does NOT wrap the insert in transaction.atomic(): joining
        the caller's transaction is the behaviour under test.
        """
        self._failures.maybe_fail("platform.record_audit")
        from shared.harness.models import HarnessAuditRecord

        HarnessAuditRecord.objects.create(
            audit_id=record.audit_id,
            school_id=record.school_id,
            actor_id=record.actor_id,
            action=record.action,
            resource_id=record.resource_id,
            occurred_at=record.occurred_at,
            request_id=record.request_id,
            before=dict(record.before),
            after=dict(record.after),
        )

    def append_event(self, event: EventEnvelope) -> None:
        """Insert one outbox row using the caller's open transaction."""
        self._failures.maybe_fail("platform.append_event")
        from shared.harness.models import HarnessOutboxEvent

        HarnessOutboxEvent.objects.create(
            event_id=event.event_id,
            school_id=event.school_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            aggregate_id=event.aggregate_id,
            aggregate_version=event.aggregate_version,
            payload=dict(event.payload),
            envelope_version=event.envelope_version,
        )

    # --- asynchronous work -------------------------------------------------

    def enqueue(self, task_path: str, *, payload: dict[str, object]) -> str:
        """Dispatch background work, or refuse when there is no real worker.

        Raises EagerModeNotAsserted when ``worker_available`` is False. This is
        intentional: a test that needs retry semantics must run against a real
        broker, and one that does not should not be calling enqueue.
        """
        self._failures.maybe_fail("platform.enqueue")
        if not self._worker_available:
            raise EagerModeNotAsserted(
                f"enqueue({task_path!r}) requires a real broker and worker; "
                "this profile has none, so asynchronous behaviour cannot be "
                "asserted. Start the module's worker service or drop the test."
            )
        from uuid import uuid4

        job_id = str(uuid4())
        self.enqueued.append(EnqueuedJob(job_id, task_path, dict(payload)))
        return job_id

    # --- rollback assertion helpers ---------------------------------------

    def audit_rows(self, *, school_id: UUID | None = None) -> list[dict[str, object]]:
        """Return audit rows currently visible, for rollback assertions.

        Called after a transaction rolls back to assert the count is zero, and
        after commit to assert the row is present.
        """
        from shared.harness.models import HarnessAuditRecord

        queryset = HarnessAuditRecord.objects.all()
        if school_id is not None:
            queryset = queryset.filter(school_id=school_id)
        return list(queryset.values())

    def outbox_rows(self, *, school_id: UUID | None = None) -> list[dict[str, object]]:
        """Return outbox rows currently visible, for rollback assertions."""
        from shared.harness.models import HarnessOutboxEvent

        queryset = HarnessOutboxEvent.objects.all()
        if school_id is not None:
            queryset = queryset.filter(school_id=school_id)
        return list(queryset.values())

    @property
    def supports_worker_assertions(self) -> bool:
        """Return whether this profile can honestly assert async behaviour."""
        return self._worker_available
