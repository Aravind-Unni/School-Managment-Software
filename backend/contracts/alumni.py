"""Alumni DTOs and AlumniPort. Owned by M10.

Frozen under school-contracts-v11. No Django imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext


@dataclass(frozen=True, slots=True)
class ContactPreferenceView:
    """One contact preference row for an alumni profile."""

    person_id: UUID
    purpose: str
    channel: str
    allowed: bool
    updated_at: str


@dataclass(frozen=True, slots=True)
class AlumniProfileView:
    """Approved alumni contact view for service consumers.

    Does not carry editable grade or transcript fields.
    """

    id: UUID
    student_id: UUID
    leaving_year: int
    outcome: str
    approved_contact_fields: dict[str, str | None]
    preferences: list[ContactPreferenceView]


@dataclass(frozen=True, slots=True)
class CreateCandidateResult:
    """Result of idempotent candidate creation."""

    id: UUID
    state: str


@runtime_checkable
class AlumniPort(Protocol):
    """Alumni profile lookup and candidate creation. Owned by M10."""

    def get_profile(
        self,
        context: RequestContext,
        student_id: UUID,
    ) -> AlumniProfileView:
        """Return approved profile contact view for student_id in actor school.

        Raises ObjectInaccessible when absent, other-school, or denied.
        Does not return editable grade or transcript fields.
        """
        ...

    def create_candidate(
        self,
        context: RequestContext,
        student_id: UUID,
        leaving_event_id: UUID,
        outcome: str,
    ) -> CreateCandidateResult:
        """Idempotent candidate for (student_id, leaving_event_id).

        Duplicate leaving_event_id returns the existing candidate id/state.
        Does not auto-create a public directory profile.
        """
        ...
