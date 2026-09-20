"""Audit and outbox writes, built once so every call site agrees on the shape.

Both join the CALLER's transaction: the Platform adapter opens none of its own, so
a rollback removes them. That is asserted by the suite, not assumed.

The publication notification is an outbox row and never a direct send. "Notify on
publication only after transaction commit; SMS outage cannot prevent timetable
publication" is exactly what an outbox row plus a separate relay gives, which is
why this module consumes no NotificationPort at all.

Does not handle: delivery. A relay moves committed rows to the broker; M14 owns it.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext


def record_audit(
    platform: object,
    context: RequestContext,
    *,
    action: str,
    resource_id: UUID,
    before: Mapping[str, object],
    after: Mapping[str, object],
    now: datetime,
) -> None:
    """Append one audit row for a critical write, inside the caller's transaction.

    ``before`` and ``after`` are REDACTED summaries -- ids, states and counts --
    never whole rows. An audit trail that copied every field would duplicate the
    record it describes and would age into a second, divergent source of truth.
    """
    platform.record_audit(
        AuditRecord(
            audit_id=uuid.uuid4(),
            school_id=context.school_id,
            actor_id=context.actor_id,
            action=action,
            resource_id=resource_id,
            occurred_at=now,
            request_id=context.request_id,
            before=dict(before),
            after=dict(after),
        )
    )


def append_event(
    platform: object,
    context: RequestContext,
    *,
    event_type: str,
    aggregate_id: UUID,
    aggregate_version: int,
    payload: Mapping[str, object],
    now: datetime,
) -> None:
    """Append one outbox row inside the caller's transaction.

    ``event_type`` is lowercase and two segments, which is what the frozen common
    envelope accepts. The packet's names (``TimetablePublished.v1``) do not match
    that pattern; review item 1 chose to conform rather than revise a shared schema
    every module and the outbox depend on. The mapping is recorded in
    contracts/M03/schemas/events.schema.json.
    """
    platform.append_event(
        EventEnvelope(
            event_id=uuid.uuid4(),
            school_id=context.school_id,
            event_type=event_type,
            occurred_at=now,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
            payload=dict(payload),
            correlation_id=context.request_id,
        )
    )
