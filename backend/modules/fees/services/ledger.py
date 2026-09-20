"""Pure balance derivation from charges, allocations and credits."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import UUID

from contracts.fees import BalanceDTO

from ..models import Allocation, Charge, Credit


def charge_status_for(balance_paise: int, amount_paise: int) -> str:
    """Derive charge status from remaining balance. Never uses float."""
    if balance_paise <= 0:
        return "paid"
    if balance_paise >= amount_paise:
        return "open"
    return "partial"


def compute_balance(
    *,
    school_id: UUID,
    student_id: UUID,
    as_of: date,
) -> BalanceDTO:
    """Sum ledger totals for one student as of a school civil date.

    Overdue is open balance on charges with due_date <= as_of. Reversed
    allocations are excluded. Does not invent late fees.
    """
    charges = list(Charge.objects.filter(school_id=school_id, student_id=student_id))
    charged = sum(c.amount_paise for c in charges)
    outstanding = sum(c.balance_paise for c in charges)
    overdue = sum(
        c.balance_paise for c in charges if c.due_date <= as_of and c.balance_paise > 0
    )

    credit_rows = list(Credit.objects.filter(school_id=school_id, student_id=student_id))
    credited = sum(c.amount_paise for c in credit_rows if c.charge_id is not None)
    credit_available = sum(
        c.remaining_paise for c in credit_rows if c.charge_id is None
    )

    paid = sum(
        a.amount_paise
        for a in Allocation.objects.filter(
            school_id=school_id, payment__student_id=student_id, reversed=False
        )
    )

    return BalanceDTO(
        student_id=student_id,
        charged_paise=charged,
        credited_paise=credited,
        paid_paise=paid,
        outstanding_paise=outstanding,
        overdue_paise=overdue,
        credit_available_paise=credit_available,
        as_of=as_of,
    )


def fingerprint_payload(parts: dict[str, object]) -> str:
    """Stable sha256 hex of a sorted JSON payload for idempotency."""
    encoded = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
