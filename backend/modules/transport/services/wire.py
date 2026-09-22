"""DTO serialisation helpers for transport API responses."""

from __future__ import annotations

from ..models import AdjustmentRequest, BillingRequest, Bus, Participation


def bus_to_wire(bus: Bus) -> dict:
    """Serialise a Bus row."""
    return {
        "id": str(bus.id),
        "school_id": str(bus.school_id),
        "label": bus.label,
        "active": bus.active,
        "version": bus.version,
        "fee_plan_id": str(bus.fee_plan_id) if bus.fee_plan_id else None,
        "monthly_fee_paise": bus.monthly_fee_paise,
    }


def participation_to_wire(row: Participation) -> dict:
    """Serialise a Participation row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "student_id": str(row.student_id),
        "bus_id": str(row.bus_id) if row.bus_id else None,
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat() if row.to_date else None,
        "fee_plan_id": str(row.fee_plan_id),
        "version": row.version,
    }


def billing_request_to_wire(row: BillingRequest) -> dict:
    """Serialise a BillingRequest row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "participation_id": str(row.participation_id),
        "period": row.period,
        "source_key": row.source_key,
        "state": row.state,
        "charge_id": str(row.charge_id) if row.charge_id else None,
        "error_code": row.error_code,
        "amount_paise": row.amount_paise,
        "version": row.version,
    }


def adjustment_to_wire(row: AdjustmentRequest) -> dict:
    """Serialise an AdjustmentRequest row."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "source_key": row.source_key,
        "charge_id": str(row.charge_id),
        "amount_paise": row.amount_paise,
        "reason": row.reason,
        "state": row.state,
        "credit_id": str(row.credit_id) if row.credit_id else None,
        "error_code": row.error_code,
        "version": row.version,
    }
