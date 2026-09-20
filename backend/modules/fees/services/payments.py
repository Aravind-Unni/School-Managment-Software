"""Manual payment posting with allocations, idempotency and receipt numbers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.db.models import F

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.events import AuditRecord, EventEnvelope
from contracts.identity import RequestContext
from contracts.values import school_date

from ..models import (
    Allocation,
    Charge,
    Credit,
    CreditKind,
    Payment,
    PaymentIdempotency,
    PaymentMethod,
    ReceiptSequence,
)
from .authority import AuthorityGate
from .ledger import charge_status_for, compute_balance, fingerprint_payload
from .wire import balance_to_wire, payment_to_wire


def _allocate_receipt_number(school_id: UUID, civil_date, now) -> str:
    """Allocate the next RCP-YYYYMMDD-##### under a row lock."""
    seq, _ = ReceiptSequence.objects.select_for_update().get_or_create(
        school_id=school_id,
        civil_date=civil_date,
        defaults={"next_value": 1},
    )
    value = seq.next_value
    ReceiptSequence.objects.filter(id=seq.id).update(next_value=F("next_value") + 1)
    return f"RCP-{civil_date.strftime('%Y%m%d')}-{value:05d}"


@dataclass(frozen=True, slots=True)
class PaymentService:
    """Record staff payments with locked allocations."""

    gate: AuthorityGate
    registry: object
    platform: object
    clock: object

    def create(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        amount_paise: int,
        method: str,
        reference: str | None,
        allocations: list[dict],
        idempotency_key: str | None,
    ) -> tuple[dict, int]:
        """Post a payment. Returns (receipt_wire, http_status 200|201)."""
        self.gate.require_staff_action(context, "fees.record_payment", student_id=student_id)
        if not idempotency_key:
            raise ValidationFailed("fees.error.idempotency_key_required")
        if amount_paise <= 0:
            raise ValidationFailed("fees.error.amount_not_positive")
        if method not in {m.value for m in PaymentMethod}:
            raise ValidationFailed("fees.error.invalid_method")
        if not allocations:
            raise ValidationFailed("fees.error.allocation_mismatch")

        student = self.registry.get_student(context, student_id)
        if student.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")

        alloc_sum = sum(int(a["amount_paise"]) for a in allocations)
        if alloc_sum > amount_paise:
            raise ValidationFailed("fees.error.allocation_mismatch")
        for row in allocations:
            if int(row["amount_paise"]) <= 0:
                raise ValidationFailed("fees.error.amount_not_positive")

        fingerprint = fingerprint_payload(
            {
                "student_id": str(student_id),
                "amount_paise": amount_paise,
                "method": method,
                "reference": reference,
                "allocations": [
                    {
                        "charge_id": str(a["charge_id"]),
                        "amount_paise": int(a["amount_paise"]),
                    }
                    for a in sorted(allocations, key=lambda x: str(x["charge_id"]))
                ],
            }
        )

        existing = (
            PaymentIdempotency.objects.filter(
                school_id=context.school_id, idempotency_key=idempotency_key
            )
            .select_related("payment")
            .first()
        )
        if existing is not None:
            if existing.payload_fingerprint != fingerprint:
                raise StateConflict("fees.error.idempotency_payload_conflict")
            payment = existing.payment
            balance = compute_balance(
                school_id=context.school_id,
                student_id=student_id,
                as_of=school_date(self.clock.now()),
            )
            return (
                {"payment": payment_to_wire(payment), "balance": balance_to_wire(balance)},
                200,
            )

        now = self.clock.now()
        civil = school_date(now)
        with transaction.atomic():
            # Re-check idempotency under lock race
            raced = (
                PaymentIdempotency.objects.select_for_update()
                .filter(school_id=context.school_id, idempotency_key=idempotency_key)
                .first()
            )
            if raced is not None:
                if raced.payload_fingerprint != fingerprint:
                    raise StateConflict("fees.error.idempotency_payload_conflict")
                payment = raced.payment
                balance = compute_balance(
                    school_id=context.school_id,
                    student_id=student_id,
                    as_of=civil,
                )
                return (
                    {
                        "payment": payment_to_wire(payment),
                        "balance": balance_to_wire(balance),
                    },
                    200,
                )

            number = _allocate_receipt_number(context.school_id, civil, now)
            payment = Payment.objects.create(
                school_id=context.school_id,
                student_id=student_id,
                number=number,
                amount_paise=amount_paise,
                method=method,
                reference=reference,
                posted_at=now,
                remaining_paise=amount_paise,
                version=1,
            )

            remaining_payment = amount_paise
            for row in allocations:
                charge = (
                    Charge.objects.select_for_update()
                    .filter(id=row["charge_id"], school_id=context.school_id)
                    .first()
                )
                if charge is None or charge.student_id != student_id:
                    raise ObjectInaccessible("error.object_inaccessible")
                amount = int(row["amount_paise"])
                if amount > charge.balance_paise or amount > remaining_payment:
                    raise StateConflict("fees.error.allocation_exceeds_available")
                Allocation.objects.create(
                    school_id=context.school_id,
                    payment=payment,
                    charge=charge,
                    amount_paise=amount,
                )
                charge.balance_paise -= amount
                charge.status = charge_status_for(charge.balance_paise, charge.amount_paise)
                charge.version += 1
                charge.save(update_fields=["balance_paise", "status", "version"])
                remaining_payment -= amount

            payment.remaining_paise = remaining_payment
            payment.save(update_fields=["remaining_paise"])

            if remaining_payment > 0:
                Credit.objects.create(
                    school_id=context.school_id,
                    student_id=student_id,
                    charge=None,
                    amount_paise=remaining_payment,
                    remaining_paise=remaining_payment,
                    reason="Overpayment credit",
                    source_key=f"overpayment:{payment.id}",
                    kind=CreditKind.OVERPAYMENT,
                    posted_at=now,
                    payload_fingerprint=fingerprint_payload(
                        {"payment_id": str(payment.id), "amount": remaining_payment}
                    ),
                )

            PaymentIdempotency.objects.create(
                school_id=context.school_id,
                idempotency_key=idempotency_key,
                payload_fingerprint=fingerprint,
                payment=payment,
            )
            self.platform.record_audit(
                AuditRecord(
                    audit_id=uuid.uuid4(),
                    school_id=context.school_id,
                    actor_id=context.actor_id,
                    action="fees.payment_posted",
                    resource_id=payment.id,
                    occurred_at=now,
                    request_id=context.request_id,
                    after={"number": number, "amount_paise": amount_paise},
                )
            )
            self.platform.append_event(
                EventEnvelope(
                    event_id=uuid.uuid4(),
                    school_id=context.school_id,
                    event_type="fees.payment_posted",
                    occurred_at=now,
                    aggregate_id=payment.id,
                    aggregate_version=payment.version,
                    payload={
                        "payment_id": str(payment.id),
                        "student_id": str(student_id),
                        "receipt_number": number,
                    },
                    correlation_id=context.request_id,
                )
            )
            balance = compute_balance(
                school_id=context.school_id, student_id=student_id, as_of=civil
            )
        return (
            {"payment": payment_to_wire(payment), "balance": balance_to_wire(balance)},
            201,
        )

    def get(self, context: RequestContext, payment_id: UUID) -> dict:
        """Fetch one payment for fees.read."""
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist as exc:
            raise ObjectInaccessible("error.object_inaccessible") from exc
        if payment.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        self.gate.require_statement_read(context, payment.student_id)
        return payment_to_wire(payment)
