"""Billing reconciliation kinds against Fees stored charges."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contracts.identity import RequestContext

from ..models import BillingRequest, BillingRequestState, ChargeKind, Participation
from .authority import AuthorityGate
from .period import overlaps_period, source_key_for


@dataclass(frozen=True, slots=True)
class ReconciliationService:
    """Compare participations, BillingRequests and FakeFees charges."""

    gate: AuthorityGate
    fees: object

    def reconcile(self, context: RequestContext, *, period: str) -> dict:
        """Return unmatched and retryable items for one billing period."""
        self.gate.require_action(context, "transport.bill")
        items: list[dict] = []
        seen_participation_ids: set[UUID] = set()

        requests = list(
            BillingRequest.objects.filter(
                school_id=context.school_id,
                period=period,
                charge_kind=ChargeKind.PERIOD,
            )
        )
        for row in requests:
            seen_participation_ids.add(row.participation_id)
            fees_charge = self.fees.get_by_source_key(row.source_key)
            if row.state == BillingRequestState.BLOCKED:
                items.append(
                    _item(
                        kind="blocked",
                        owner="transport",
                        period=period,
                        retryable=False,
                        participation_id=row.participation_id,
                        billing_request_id=row.id,
                        source_key=row.source_key,
                        charge_id=row.charge_id,
                        state=row.state,
                        error_code=row.error_code,
                    )
                )
                continue
            if row.state == BillingRequestState.FAILED:
                items.append(
                    _item(
                        kind="retryable_failure",
                        owner="transport",
                        period=period,
                        retryable=True,
                        participation_id=row.participation_id,
                        billing_request_id=row.id,
                        source_key=row.source_key,
                        charge_id=row.charge_id,
                        state=row.state,
                        error_code=row.error_code,
                    )
                )
                continue
            if row.state == BillingRequestState.REQUESTED and row.charge_id is None:
                if fees_charge is not None:
                    items.append(
                        _item(
                            kind="orphaned_link",
                            owner="fees",
                            period=period,
                            retryable=True,
                            participation_id=row.participation_id,
                            billing_request_id=row.id,
                            source_key=row.source_key,
                            charge_id=fees_charge.id,
                            state=row.state,
                            error_code=row.error_code,
                        )
                    )
                else:
                    items.append(
                        _item(
                            kind="retryable_failure",
                            owner="transport",
                            period=period,
                            retryable=True,
                            participation_id=row.participation_id,
                            billing_request_id=row.id,
                            source_key=row.source_key,
                            charge_id=None,
                            state=row.state,
                            error_code=row.error_code,
                        )
                    )
                continue
            if row.charge_id is not None and fees_charge is None:
                items.append(
                    _item(
                        kind="orphaned_link",
                        owner="transport",
                        period=period,
                        retryable=False,
                        participation_id=row.participation_id,
                        billing_request_id=row.id,
                        source_key=row.source_key,
                        charge_id=row.charge_id,
                        state=row.state,
                        error_code=row.error_code,
                    )
                )

        for participation in Participation.objects.filter(school_id=context.school_id):
            if participation.id in seen_participation_ids:
                continue
            if not overlaps_period(
                from_date=participation.from_date,
                to_date=participation.to_date,
                period=period,
            ):
                continue
            key = source_key_for(participation.id, period, ChargeKind.PERIOD)
            items.append(
                _item(
                    kind="missing_charge",
                    owner="transport",
                    period=period,
                    retryable=True,
                    participation_id=participation.id,
                    billing_request_id=None,
                    source_key=key,
                    charge_id=None,
                    state=None,
                    error_code=None,
                )
            )
        return {"period": period, "items": items}


def _item(
    *,
    kind: str,
    owner: str,
    period: str,
    retryable: bool,
    participation_id: UUID | None,
    billing_request_id: UUID | None,
    source_key: str | None,
    charge_id: UUID | None,
    state: str | None,
    error_code: str | None,
) -> dict:
    """Build one ReconciliationItemDTO wire object."""
    return {
        "kind": kind,
        "owner": owner,
        "period": period,
        "retryable": retryable,
        "participation_id": str(participation_id) if participation_id else None,
        "billing_request_id": str(billing_request_id) if billing_request_id else None,
        "source_key": source_key,
        "charge_id": str(charge_id) if charge_id else None,
        "state": state,
        "error_code": error_code,
    }
