"""Reversals, concessions and refunds."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from contracts.errors import (
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)
from contracts.events import AuditRecord, EventEnvelope
from contracts.fees import CreditDTO
from contracts.identity import RequestContext
from contracts.values import school_date

from ..models import Allocation, Charge, Credit, CreditKind, Payment, RefundRecord, Reversal
from .authority import AuthorityGate
from .ledger import charge_status_for, compute_balance, fingerprint_payload
from .wire import balance_to_wire, credit_to_wire, refund_to_wire


@dataclass(frozen=True, slots=True)
class CorrectionService:
    """Posted-entry corrections: reverse, concede, refund."""

    gate: AuthorityGate
    registry: object
    platform: object
    clock: object

    def reverse_payment(
        self,
        context: RequestContext,
        payment_id: UUID,
        *,
        reason: str,
        expected_version: int,
    ) -> dict:
        """Reverse a payment and restore charge balances."""
        if not reason or not str(reason).strip():
            raise ValidationFailed("fees.error.reason_required")
        self.gate.require_staff_action(context, "fees.reverse_payment", require_2fa=True)
        now = self.clock.now()
        with transaction.atomic():
            try:
                payment = Payment.objects.select_for_update().get(id=payment_id)
            except Payment.DoesNotExist as exc:
                raise ObjectInaccessible("error.object_inaccessible") from exc
            if payment.school_id != context.school_id:
                raise ObjectInaccessible("error.object_inaccessible")
            if payment.reversed:
                raise StateConflict("fees.error.already_reversed")
            if payment.version != expected_version:
                raise VersionConflict("error.version_conflict")

            for allocation in Allocation.objects.select_for_update().filter(
                payment=payment, reversed=False
            ):
                charge = Charge.objects.select_for_update().get(id=allocation.charge_id)
                charge.balance_paise += allocation.amount_paise
                charge.status = charge_status_for(charge.balance_paise, charge.amount_paise)
                charge.version += 1
                charge.save(update_fields=["balance_paise", "status", "version"])
                allocation.reversed = True
                allocation.save(update_fields=["reversed"])

            Credit.objects.filter(
                school_id=context.school_id,
                source_key=f"overpayment:{payment.id}",
            ).update(remaining_paise=0)

            payment.reversed = True
            payment.version += 1
            payment.remaining_paise = payment.amount_paise
            payment.save(update_fields=["reversed", "version", "remaining_paise"])

            reversal = Reversal.objects.create(
                school_id=context.school_id,
                payment=payment,
                reason=reason.strip(),
                posted_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="fees.payment_reversed",
                    resource_id=payment.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"reversal_id": str(reversal.id), "reason": reason.strip()},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="fees.payment_reversed",
                    occurred_at=now,
                    aggregate_id=payment.id,
                    aggregate_version=payment.version,
                    payload={
                        "payment_id": str(payment.id),
                        "reversal_id": str(reversal.id),
                    },
                    correlation_id=context.request_id,
                )
            )
            balance = compute_balance(
                school_id=context.school_id,
                student_id=payment.student_id,
                as_of=school_date(now),
            )
        return {
            "id": str(reversal.id),
            "original_payment_id": str(payment.id),
            "reason": reason.strip(),
            "posted_at": now.isoformat(),
            "balance": balance_to_wire(balance),
        }

    def concede(
        self,
        context: RequestContext,
        *,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
        major: bool = False,
    ) -> dict:
        """Post a concession credit against one charge."""
        if not reason or not str(reason).strip():
            raise ValidationFailed("fees.error.reason_required")
        if amount_paise <= 0:
            raise ValidationFailed("fees.error.amount_not_positive")
        require_2fa = major
        self.gate.require_staff_action(context, "fees.concede", require_2fa=require_2fa)
        now = self.clock.now()
        fingerprint = fingerprint_payload(
            {
                "charge_id": str(charge_id),
                "amount_paise": amount_paise,
                "reason": reason.strip(),
            }
        )
        existing = Credit.objects.filter(
            school_id=context.school_id, source_key=source_key
        ).first()
        if existing is not None:
            if existing.payload_fingerprint != fingerprint:
                raise StateConflict("fees.error.source_key_conflict")
            return credit_to_wire(existing)

        with transaction.atomic():
            try:
                charge = Charge.objects.select_for_update().get(id=charge_id)
            except Charge.DoesNotExist as exc:
                raise ObjectInaccessible("error.object_inaccessible") from exc
            if charge.school_id != context.school_id:
                raise ObjectInaccessible("error.object_inaccessible")
            if (
                not major
                and amount_paise * 2 >= charge.balance_paise
                and charge.balance_paise > 0
            ):
                self.gate.require_staff_action(context, "fees.concede", require_2fa=True)
            if amount_paise > charge.balance_paise:
                raise StateConflict("fees.error.allocation_exceeds_available")
            charge.balance_paise -= amount_paise
            charge.status = charge_status_for(charge.balance_paise, charge.amount_paise)
            charge.version += 1
            charge.save(update_fields=["balance_paise", "status", "version"])
            credit = Credit.objects.create(
                school_id=context.school_id,
                student_id=charge.student_id,
                charge=charge,
                amount_paise=amount_paise,
                remaining_paise=0,
                reason=reason.strip(),
                source_key=source_key,
                kind=CreditKind.CONCESSION,
                posted_at=now,
                payload_fingerprint=fingerprint,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="fees.concession_posted",
                    resource_id=credit.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"amount_paise": amount_paise, "charge_id": str(charge_id)},
                )
            )
        return credit_to_wire(credit)

    def credit_charge_port(
        self,
        context: RequestContext,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
    ) -> CreditDTO:
        """FeesPort.credit_charge implementation."""
        wire = self.concede(
            context,
            charge_id=charge_id,
            amount_paise=amount_paise,
            reason=reason,
            source_key=source_key,
            major=False,
        )
        return CreditDTO(
            id=UUID(wire["id"]),
            charge_id=UUID(wire["charge_id"]) if wire["charge_id"] else None,
            amount_paise=wire["amount_paise"],
            reason=wire["reason"],
            source_key=wire["source_key"],
            student_id=UUID(wire["student_id"]),
            kind=wire["kind"],
        )

    def refund(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        amount_paise: int,
        reason: str,
        credit_id: UUID | None,
    ) -> dict:
        """Record an explicit refund against available overpayment credit."""
        if not reason or not str(reason).strip():
            raise ValidationFailed("fees.error.reason_required")
        if amount_paise <= 0:
            raise ValidationFailed("fees.error.amount_not_positive")
        self.gate.require_staff_action(
            context, "fees.refund", student_id=student_id, require_2fa=True
        )
        now = self.clock.now()
        with transaction.atomic():
            if credit_id is not None:
                credit_rows = list(
                    Credit.objects.select_for_update().filter(
                        id=credit_id,
                        school_id=context.school_id,
                        student_id=student_id,
                        charge__isnull=True,
                    )
                )
            else:
                credit_rows = list(
                    Credit.objects.select_for_update()
                    .filter(
                        school_id=context.school_id,
                        student_id=student_id,
                        charge__isnull=True,
                        remaining_paise__gt=0,
                    )
                    .order_by("posted_at")
                )
            available = sum(c.remaining_paise for c in credit_rows)
            if amount_paise > available:
                raise StateConflict("fees.error.allocation_exceeds_available")
            left = amount_paise
            primary = None
            for credit in credit_rows:
                if left <= 0:
                    break
                take = min(left, credit.remaining_paise)
                credit.remaining_paise -= take
                credit.save(update_fields=["remaining_paise"])
                left -= take
                primary = credit
            row = RefundRecord.objects.create(
                school_id=context.school_id,
                student_id=student_id,
                credit=primary,
                amount_paise=amount_paise,
                reason=reason.strip(),
                posted_at=now,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="fees.refund_posted",
                    resource_id=row.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"amount_paise": amount_paise},
                )
            )
        return refund_to_wire(row)
