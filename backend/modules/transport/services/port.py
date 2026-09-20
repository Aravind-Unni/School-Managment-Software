"""In-process TransportPort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.transport import PeriodChargeResult, TransportParticipationView

from ..models import Participation
from .authority import AuthorityGate
from .billing import BillingService


@dataclass(frozen=True, slots=True)
class TransportService:
    """Concrete TransportPort for in-process consumers."""

    gate: AuthorityGate
    billing: BillingService

    def get_participation(
        self,
        context: RequestContext,
        student_id: UUID,
        on_date: date,
    ) -> TransportParticipationView:
        """Return the participation effective on the school civil date."""
        self.gate.require_action(context, "transport.read", student_id=student_id)
        row = (
            Participation.objects.filter(
                school_id=context.school_id,
                student_id=student_id,
                from_date__lte=on_date,
            )
            .filter(
                models_to_date_open_or_after(on_date),
            )
            .order_by("-from_date")
            .first()
        )
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        active = row.to_date is None or row.to_date >= on_date
        return TransportParticipationView(
            id=row.id,
            active=active,
            from_date=row.from_date,
            fee_plan_id=row.fee_plan_id,
            bus_id=row.bus_id,
            to_date=row.to_date,
        )

    def request_period_charge(
        self,
        context: RequestContext,
        participation_id: UUID,
        period: str,
    ) -> PeriodChargeResult:
        """Delegate to BillingService.request_period_charge."""
        self.gate.require_action(context, "transport.bill")
        return self.billing.request_period_charge(context, participation_id, period)


def models_to_date_open_or_after(on_date: date):
    """Q filter: to_date is null or on_date is still within the range."""
    from django.db.models import Q

    return Q(to_date__isnull=True) | Q(to_date__gte=on_date)
