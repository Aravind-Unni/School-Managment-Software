"""Controlled NotificationPort sandbox for integrated runs.

Never contacts a real SMS or email gateway. C02 allows explicitly controlled
external-independent sandboxes; this adapter records dispatches in memory and
is marked AdapterKind.REAL only in the sense that it is the approved integrated
binding — not a silent FakeNotifications substitute for production SMS.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from contracts.identity import RequestContext


@dataclass(frozen=True, slots=True)
class SandboxDispatch:
    """One captured dispatch for assertions and operator inspection."""

    dispatch_id: str
    school_id: UUID
    channel: str
    recipients: tuple[UUID, ...]
    template_key: str
    variables: dict[str, object]


@dataclass
class ControlledSandboxNotifications:
    """Queue-shaped NotificationPort with no network code.

    Unknown channels and empty recipient lists raise ValueError so wiring typos
    fail at call time rather than disappearing into a provider log.
    """

    KNOWN_CHANNELS = frozenset({"sms", "email", "in_app"})
    sent: list[SandboxDispatch] = field(default_factory=list)

    def send(
        self,
        context: RequestContext,
        *,
        channel: str,
        recipients: Sequence[UUID],
        template_key: str,
        variables: dict[str, object],
    ) -> str:
        """Record a templated dispatch and return its id. No provider call."""
        if channel not in self.KNOWN_CHANNELS:
            raise ValueError(f"unknown channel {channel!r}")
        if not recipients:
            raise ValueError("send requires at least one recipient")
        dispatch_id = str(uuid4())
        self.sent.append(
            SandboxDispatch(
                dispatch_id=dispatch_id,
                school_id=context.school_id,
                channel=channel,
                recipients=tuple(recipients),
                template_key=template_key,
                variables=dict(variables),
            )
        )
        return dispatch_id
