"""M01's ergonomic wrapper over PlatformPort.

M01 specifies ``Platform.record_audit(ctx, action, aggregate_id, redacted_diff)``
and ``Platform.append_event(ctx, event_type, aggregate_id, aggregate_version,
payload)``. B00 froze DTO-based methods with the same names but different
signatures, and a Protocol cannot carry two signatures for one name.

Rather than change the shared contract (which would break every existing consumer
and the harness test adapter), M01 keeps the shared port intact and provides the
specified signatures here. Nothing outside M01 needs to know.

Both writes participate in the CALLER's transaction: this facade opens none, so a
rollback removes the audit row and the outbox event along with the change.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from uuid import UUID

from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.ports import PlatformPort

#: Keys that must never reach an audit row or an event payload. Redaction is
#: applied centrally here rather than trusted to each call site, because one
#: forgotten call site is a credential in a log forever.
FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "new_password",
        "code",
        "codes",
        "recovery_code",
        "recovery_codes",
        "secret",
        "secret_base32",
        "encrypted_secret",
        "otpauth_uri",
        "token",
        "token_hash",
        "session_token",
        "cookie",
    }
)

#: Replacement for a redacted value. Records that a field WAS present without
#: recording what it was, which is what an auditor needs.
REDACTED = "<redacted>"


def redact(payload: Mapping[str, object]) -> dict[str, object]:
    """Return a copy with every forbidden key replaced, recursively.

    Recurses into nested objects and lists, because a seed nested one level down is
    the interesting case. Key matching is case-insensitive.
    """
    cleaned: dict[str, object] = {}
    for key, value in payload.items():
        if key.lower() in FORBIDDEN_PAYLOAD_KEYS:
            cleaned[key] = REDACTED
        elif isinstance(value, Mapping):
            cleaned[key] = redact(value)
        elif isinstance(value, (list, tuple)):
            cleaned[key] = [
                redact(item) if isinstance(item, Mapping) else item for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


class PlatformFacade:
    """M01's view of Platform, with the signatures M01 specifies."""

    def __init__(self, *, platform: PlatformPort, clock) -> None:
        """Store the shared port and the injected clock."""
        self._platform = platform
        self._clock = clock

    def record_audit(
        self,
        context: RequestContext,
        action: str,
        aggregate_id: UUID,
        redacted_diff: Mapping[str, object],
    ) -> UUID:
        """Append an audit row inside the caller's transaction and return its id.

        ``redacted_diff`` is redacted AGAIN here even though the caller is expected
        to have done so. Double redaction costs nothing; a leaked seed is permanent.
        """
        audit_id = uuid.uuid4()
        self._platform.record_audit(
            AuditRecord(
                audit_id=audit_id,
                school_id=context.school_id,
                actor_id=context.actor_id,
                action=action,
                resource_id=aggregate_id,
                occurred_at=self._clock.now(),
                request_id=context.request_id,
                before={},
                after=redact(redacted_diff),
            )
        )
        return audit_id

    def append_event(
        self,
        context: RequestContext,
        event_type: str,
        aggregate_id: UUID,
        aggregate_version: int,
        payload: Mapping[str, object],
    ) -> UUID:
        """Append an outbox event inside the caller's transaction.

        The payload is redacted: M01's events carry ids and versions only. No
        password, OTP, seed or recovery-code value may ever appear in an event,
        because events are delivered at least once and consumers may log them.
        """
        event_id = uuid.uuid4()
        self._platform.append_event(
            EventEnvelope(
                event_id=event_id,
                school_id=context.school_id,
                event_type=event_type,
                occurred_at=self._clock.now(),
                aggregate_id=aggregate_id,
                aggregate_version=aggregate_version,
                payload=redact(payload),
                correlation_id=context.request_id,
            )
        )
        return event_id
