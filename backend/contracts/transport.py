"""Transport DTOs and TransportPort. Owned by M08.

Frozen under school-contracts-v9. No Django imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext


@dataclass(frozen=True, slots=True)
class TransportParticipationView:
    """Participation effective on one school civil date."""

    id: UUID
    active: bool
    from_date: date
    fee_plan_id: UUID
    bus_id: UUID | None = None
    to_date: date | None = None


@dataclass(frozen=True, slots=True)
class PeriodChargeResult:
    """Outcome of requesting one period charge via Fees."""

    source_key: str
    state: str
    charge_id: UUID | None = None


@runtime_checkable
class TransportPort(Protocol):
    """Bus participation lookup and period charge requests. Owned by M08."""

    def get_participation(
        self,
        context: RequestContext,
        student_id: UUID,
        on_date: date,
    ) -> TransportParticipationView:
        """Return the participation effective on the school civil date.

        Raises ObjectInaccessible when the student is absent or other-school,
        or when no participation covers that date.
        """
        ...

    def request_period_charge(
        self,
        context: RequestContext,
        participation_id: UUID,
        period: str,
    ) -> PeriodChargeResult:
        """Request Fees.raise_charge for one participation/period.

        source_key is transport:{participation_id}:{period}:period.
        Idempotent on source_key. Partial periods without proration policy
        return state=blocked rather than inventing an amount.
        """
        ...
