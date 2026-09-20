"""Library DTOs and LibraryPort. Owned by M09.

Frozen under school-contracts-v10. No Django imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext


@dataclass(frozen=True, slots=True)
class OpenLoanView:
    """One open loan for a borrower."""

    loan_id: UUID
    copy_id: UUID
    due_date: date
    overdue: bool


@dataclass(frozen=True, slots=True)
class AvailabilityView:
    """Copy counts for one title. total excludes withdrawn."""

    available: int
    total: int


@runtime_checkable
class LibraryPort(Protocol):
    """Open-loan and availability lookup. Owned by M09."""

    def get_open_loans(
        self,
        context: RequestContext,
        person_id: UUID,
    ) -> list[OpenLoanView]:
        """Return open loans for person_id in the actor school.

        Raises ObjectInaccessible when person is other-school or denied.
        """
        ...

    def get_availability(
        self,
        context: RequestContext,
        title_id: UUID,
    ) -> AvailabilityView:
        """Return available and total (non-withdrawn) copy counts.

        Raises ObjectInaccessible when title absent or other-school.
        """
        ...
