"""In-memory fake NotificationPort. Never contacts a real provider.

B00 requires that local and test profiles cannot reach a real SMS or email
gateway. This adapter has no network code at all, which is a stronger guarantee
than a disabled credential.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from contracts.identity import RequestContext

from .failures import FailureInjector


@dataclass(frozen=True, slots=True)
class SentMessage:
    """One message the fake captured instead of sending."""

    dispatch_id: str
    school_id: UUID
    channel: str
    recipients: tuple[UUID, ...]
    template_key: str
    variables: dict[str, object]


class FakeNotifications:
    """Records messages in memory for assertion.

    Tests read ``adapter.sent`` rather than inspecting logs, so an assertion
    failure names the template and recipients directly.
    """

    #: Channels the fake accepts. An unknown channel raises, so a typo in a
    #: template wiring is caught in development rather than silently dropped.
    KNOWN_CHANNELS = frozenset({"sms", "email", "in_app"})

    def __init__(self, *, failures: FailureInjector | None = None) -> None:
        """Build the adapter with an empty outbox."""
        self.sent: list[SentMessage] = []
        self._failures = failures or FailureInjector()

    def send(
        self,
        context: RequestContext,
        *,
        channel: str,
        recipients: Sequence[UUID],
        template_key: str,
        variables: dict[str, object],
    ) -> str:
        """Capture a message and return a synthetic dispatch id.

        Raises ValueError on an unknown channel or an empty recipient list.

        Does not handle: templating or localisation. The fake stores variables
        verbatim; rendering English/Malayalam text is M11's job.
        """
        self._failures.maybe_fail("notifications.send")
        if channel not in self.KNOWN_CHANNELS:
            raise ValueError(f"unknown channel {channel!r}")
        if not recipients:
            raise ValueError("send requires at least one recipient")
        dispatch_id = str(uuid4())
        self.sent.append(
            SentMessage(
                dispatch_id=dispatch_id,
                school_id=context.school_id,
                channel=channel,
                recipients=tuple(recipients),
                template_key=template_key,
                variables=dict(variables),
            )
        )
        return dispatch_id

    def messages_for(self, recipient_id: UUID) -> tuple[SentMessage, ...]:
        """Return captured messages addressed to one person."""
        return tuple(m for m in self.sent if recipient_id in m.recipients)
