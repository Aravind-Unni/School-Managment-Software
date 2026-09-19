"""The single outbox event envelope shared by all modules.

Every cross-module notification uses this envelope. A module may define its own
``payload`` schema, but never its own envelope fields: a new top-level key is a
contract revision, not a per-module adapter.

Does not handle: delivery, ordering across aggregates, or retry. PlatformPort
owns those; this is only the record shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

#: Bumped only by a reviewed contract revision.
EVENT_ENVELOPE_VERSION = 1


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """One durable domain event appended inside the writer's transaction.

    ``event_type`` is dotted and owned by the emitting module
    (``assessment.result_published``). ``aggregate_version`` is the version of
    the aggregate *after* the write, letting consumers detect gaps.

    Does not handle: payload validation. The contract suite validates payloads
    against the module's JSON Schema at test time.
    """

    event_id: UUID
    school_id: UUID
    event_type: str
    occurred_at: datetime
    aggregate_id: UUID
    aggregate_version: int
    payload: Mapping[str, object] = field(default_factory=dict)
    envelope_version: int = EVENT_ENVELOPE_VERSION
    #: Correlates every event emitted while handling one request. Added for M01.
    #: None is allowed so a worker-originated event need not invent one.
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        """Freeze the payload and require a namespaced type and aware timestamp.

        The payload is copied into a read-only mapping: a frozen dataclass still
        shares a mutable dict with its caller, so without this an event already
        appended to the outbox could be altered through the caller's reference.
        """
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if "." not in self.event_type:
            raise ValueError(f"event_type must be '<module>.<event>': {self.event_type!r}")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware UTC")

    def to_wire(self) -> dict[str, object]:
        """Serialise for the outbox table and for consumer fixtures."""
        return {
            "event_id": str(self.event_id),
            "school_id": str(self.school_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": str(self.aggregate_id),
            "aggregate_version": self.aggregate_version,
            "payload": dict(self.payload),
            # Both keys carry the same number. M01 specifies "schema_version";
            # B00 froze "envelope_version" and consumer fixtures assert it. Both
            # are emitted for one revision so neither side breaks; the
            # school-contracts-v4 revision should retire "envelope_version".
            "schema_version": self.envelope_version,
            "envelope_version": self.envelope_version,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """One append-only record of a critical write.

    Written in the same transaction as the change it describes, so a rolled-back
    write leaves no audit row and a committed write always has one.
    """

    audit_id: UUID
    school_id: UUID
    actor_id: UUID
    action: str
    resource_id: UUID
    occurred_at: datetime
    request_id: str
    before: Mapping[str, object] = field(default_factory=dict)
    after: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze the before/after mappings against later caller mutation."""
        object.__setattr__(self, "before", MappingProxyType(dict(self.before)))
        object.__setattr__(self, "after", MappingProxyType(dict(self.after)))

    def to_wire(self) -> dict[str, object]:
        """Serialise for the audit table and rollback assertions."""
        return {
            "audit_id": str(self.audit_id),
            "school_id": str(self.school_id),
            "actor_id": str(self.actor_id),
            "action": self.action,
            "resource_id": str(self.resource_id),
            "occurred_at": self.occurred_at.isoformat(),
            "request_id": self.request_id,
            "before": dict(self.before),
            "after": dict(self.after),
        }
