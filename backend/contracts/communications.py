"""Communications DTOs and CommunicationsPort. Owned by M11.

Frozen under school-contracts-v12. No Django imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext


@dataclass(frozen=True, slots=True)
class DeliveryDTO:
    """One outbound delivery row returned to callers.

    Does not include phone numbers or secret material.
    """

    id: UUID
    state: str


@runtime_checkable
class CommunicationsPort(Protocol):
    """In-app notices and replaceable outbound messaging. Owned by M11."""

    def enqueue(
        self,
        context: RequestContext,
        template_key: str,
        recipient_ref: UUID,
        channel: str,
        locale: str,
        variables: dict[str, object],
        dedupe_key: str,
    ) -> DeliveryDTO:
        """Queue one templated delivery; identical keys return the same row.

        recipient_ref is a verified school person/contact id, not arbitrary
        client text. Same dedupe_key with a different payload_hash raises
        StateConflict. Does not send passwords, TOTP secrets, evidence URLs
        or detailed grades.
        """
        ...
