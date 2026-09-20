"""Adjustment requests that credit posted bus charges via FeesPort."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import ObjectInaccessible, ValidationFailed
from contracts.events import AuditRecord
from contracts.identity import RequestContext

from ..models import AdjustmentRequest, AdjustmentRequestState
from .authority import AuthorityGate
from .wire import adjustment_to_wire


@dataclass(frozen=True, slots=True)
class AdjustmentService:
    """Create AdjustmentRequest rows and call Fees.credit_charge."""

    gate: AuthorityGate
    fees: object
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
    ) -> dict:
        """Request an explicit Fees credit; never deletes old invoices."""
        self.gate.require_action(context, "transport.bill")
        if amount_paise < 1:
            raise ValidationFailed("error.validation_failed")
        if not reason or not reason.strip():
            raise ValidationFailed("transport.error.reason_required")
        if not source_key.strip():
            raise ValidationFailed("error.validation_failed")
        matched = next(
            (
                c
                for c in self.fees.list_charges()
                if c.id == charge_id and c.school_id == context.school_id
            ),
            None,
        )
        if matched is None:
            raise ObjectInaccessible("error.object_inaccessible")
        now = self.clock.now()
        with transaction.atomic():
            row = AdjustmentRequest.objects.create(
                school_id=context.school_id,
                source_key=source_key,
                charge_id=charge_id,
                amount_paise=amount_paise,
                reason=reason.strip(),
                state=AdjustmentRequestState.REQUESTED,
                version=1,
            )
            credit = self.fees.credit_charge(
                context,
                charge_id=charge_id,
                amount_paise=amount_paise,
                reason=reason.strip(),
                source_key=source_key,
            )
            row.credit_id = credit.id
            row.state = AdjustmentRequestState.POSTED
            row.save(update_fields=["credit_id", "state"])
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="transport.adjustment_posted",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={
                        "charge_id": str(charge_id),
                        "credit_id": str(credit.id),
                        "amount_paise": amount_paise,
                    },
                )
            )
        return adjustment_to_wire(row)
