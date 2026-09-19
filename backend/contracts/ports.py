"""Typed in-process service ports. Protocols only -- no implementations.

A module depends on these Protocols, never on another module's concrete class.
Standalone mode binds deterministic fakes; integrated mode binds real adapters.
The architecture check enforces that ``backend/modules/<a>`` never imports
``backend/modules/<b>``.

Does not handle: transport. These are in-process calls in a modular monolith;
there is no HTTP between modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable
from uuid import UUID

from .events import AuditRecord, EventEnvelope
from .evidence import EvidenceRef, ResourceGrant
from .identity import RequestContext
from .scope import RelationshipFacts, ScopeFacts


@runtime_checkable
class ClockPort(Protocol):
    """Source of time. Injected so tests control 'now' explicitly."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC instant."""
        ...


@runtime_checkable
class AccessPort(Protocol):
    """Authorisation decisions. Owned by M01 access.

    Every implementation must default to deny: an action it has no rule for is
    denied, never allowed.
    """

    def check(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> None:
        """Authorise ``action`` for the context, or raise.

        Raises ActionDenied (403), ObjectInaccessible (404) when the school does
        not match, or StaleAuth (401) when 2FA is too old for this action.
        Returns None on success so that call sites read as assertions.

        Does not handle: row filtering. A list endpoint asks for a predicate via
        ``visible_scope`` instead of checking every row.
        """
        ...

    def is_allowed(
        self,
        context: RequestContext,
        action: str,
        facts: ScopeFacts,
    ) -> bool:
        """Return whether the action is permitted, without raising.

        For building navigation and conditional UI only. Never use this in place
        of ``check`` on a write path.
        """
        ...


@runtime_checkable
class RegistryPort(Protocol):
    """People, sections and relationships. Owned by M02 registry."""

    def relationship_facts(
        self,
        context: RequestContext,
        subject_person_id: UUID,
    ) -> RelationshipFacts:
        """Return how the context's actor relates to the subject person.

        Returns Relationship.NONE rather than raising when unrelated, because
        'unrelated' is a normal policy input, not an error.

        Does not handle: authorising the caller to see the subject. The caller
        folds this into ScopeFacts and asks Access.
        """
        ...


@runtime_checkable
class PlatformPort(Protocol):
    """Audit, outbox and background jobs. Owned by M14 platform.

    Both writes MUST join the caller's open database transaction so that a
    rollback removes them. The test adapter asserts exactly that.
    """

    def record_audit(self, record: AuditRecord) -> None:
        """Append an audit row inside the caller's transaction."""
        ...

    def append_event(self, event: EventEnvelope) -> None:
        """Append an outbox row inside the caller's transaction.

        Does not handle: publishing. A separate relay moves committed rows to
        the broker, so an uncommitted event is never delivered.
        """
        ...

    def enqueue(self, task_path: str, *, payload: dict[str, object]) -> str:
        """Schedule background work and return its job id.

        Does not handle: result retrieval. Jobs report through their own
        aggregates, not through return values.
        """
        ...


@runtime_checkable
class ObjectStoragePort(Protocol):
    """Private object storage. Owned by M12 files."""

    def put(
        self,
        context: RequestContext,
        *,
        storage_key: str,
        content_type: str,
        body: bytes,
    ) -> EvidenceRef:
        """Store bytes under the school's private prefix and return a ref."""
        ...

    def signed_read_url(
        self,
        ref: EvidenceRef,
        *,
        grant: ResourceGrant,
        expires_in_seconds: int,
    ) -> str:
        """Mint a short-lived read URL for an already-authorised grant.

        Assumes the caller has run an Access check and minted ``grant``.
        Implementations must reject an expired grant rather than trusting it.
        """
        ...


@runtime_checkable
class NotificationPort(Protocol):
    """Outbound messages. Owned by M11 communications.

    Local and test profiles must never reach a real SMS or email provider; the
    fake records messages in memory for assertion.
    """

    def send(
        self,
        context: RequestContext,
        *,
        channel: str,
        recipients: Sequence[UUID],
        template_key: str,
        variables: dict[str, object],
    ) -> str:
        """Queue a templated message and return its dispatch id."""
        ...
