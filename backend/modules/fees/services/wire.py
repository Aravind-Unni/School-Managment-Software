"""DTO serialisation helpers for fees API responses."""

from __future__ import annotations

from contracts.fees import BalanceDTO

from ..models import Allocation, Charge, Credit, FeeHead, FeePlan, Payment, RefundRecord


def fee_head_to_wire(head: FeeHead) -> dict:
    """Serialise a FeeHead row."""
    return {
        "id": str(head.id),
        "school_id": str(head.school_id),
        "code": head.code,
        "label_key": head.label_key,
        "version": head.version,
    }


def fee_plan_to_wire(plan: FeePlan, heads: list[FeeHead]) -> dict:
    """Serialise a FeePlan with its heads."""
    return {
        "id": str(plan.id),
        "school_id": str(plan.school_id),
        "version": plan.version,
        "applicability": plan.applicability,
        "schedule": plan.schedule,
        "fee_heads": [fee_head_to_wire(h) for h in heads],
    }


def charge_to_wire(charge: Charge) -> dict:
    """Serialise a Charge row."""
    return {
        "id": str(charge.id),
        "school_id": str(charge.school_id),
        "student_id": str(charge.student_id),
        "fee_head_id": str(charge.fee_head_id),
        "source_key": charge.source_key,
        "amount_paise": charge.amount_paise,
        "balance_paise": charge.balance_paise,
        "due_date": charge.due_date.isoformat(),
        "status": charge.status,
        "description_key": charge.description_key,
        "version": charge.version,
    }


def allocation_to_wire(row: Allocation) -> dict:
    """Serialise an Allocation row."""
    return {
        "id": str(row.id),
        "payment_id": str(row.payment_id),
        "charge_id": str(row.charge_id),
        "amount_paise": row.amount_paise,
    }


def payment_to_wire(payment: Payment) -> dict:
    """Serialise a Payment with its allocations."""
    allocations = [
        allocation_to_wire(a)
        for a in Allocation.objects.filter(payment=payment, reversed=False).order_by("id")
    ]
    return {
        "id": str(payment.id),
        "school_id": str(payment.school_id),
        "student_id": str(payment.student_id),
        "number": payment.number,
        "amount_paise": payment.amount_paise,
        "method": payment.method,
        "reference": payment.reference,
        "posted_at": payment.posted_at.isoformat(),
        "allocations": allocations,
        "reversed": payment.reversed,
        "version": payment.version,
    }


def credit_to_wire(credit: Credit) -> dict:
    """Serialise a Credit row."""
    return {
        "id": str(credit.id),
        "charge_id": str(credit.charge_id) if credit.charge_id else None,
        "student_id": str(credit.student_id),
        "amount_paise": credit.amount_paise,
        "reason": credit.reason,
        "source_key": credit.source_key,
        "kind": credit.kind,
    }


def refund_to_wire(row: RefundRecord) -> dict:
    """Serialise a RefundRecord row."""
    return {
        "id": str(row.id),
        "student_id": str(row.student_id),
        "amount_paise": row.amount_paise,
        "reason": row.reason,
        "credit_id": str(row.credit_id) if row.credit_id else None,
        "posted_at": row.posted_at.isoformat(),
    }


def balance_to_wire(balance: BalanceDTO) -> dict:
    """Serialise a BalanceDTO."""
    return {
        "student_id": str(balance.student_id) if balance.student_id else None,
        "charged_paise": balance.charged_paise,
        "credited_paise": balance.credited_paise,
        "paid_paise": balance.paid_paise,
        "outstanding_paise": balance.outstanding_paise,
        "overdue_paise": balance.overdue_paise,
        "credit_available_paise": balance.credit_available_paise,
        "as_of": balance.as_of.isoformat(),
    }
