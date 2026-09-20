"""Fee ledger DTOs. Owned by M07.

Frozen under school-contracts-v8. No Django imports. Amounts are integer INR paise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext


@dataclass(frozen=True, slots=True)
class ChargeDTO:
    """One posted charge on the student ledger."""

    id: UUID
    source_key: str
    amount_paise: int
    balance_paise: int
    status: str
    student_id: UUID | None = None
    fee_head_id: UUID | None = None
    due_date: date | None = None
    school_id: UUID | None = None
    description_key: str | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class CreditDTO:
    """Concession, overpayment or adjustment credit."""

    id: UUID
    charge_id: UUID | None
    amount_paise: int
    reason: str | None = None
    source_key: str | None = None
    student_id: UUID | None = None
    kind: str = "concession"


@dataclass(frozen=True, slots=True)
class BalanceDTO:
    """Derived ledger totals for one student as of a school civil date."""

    charged_paise: int
    credited_paise: int
    paid_paise: int
    outstanding_paise: int
    overdue_paise: int
    as_of: date
    student_id: UUID | None = None
    credit_available_paise: int = 0


@runtime_checkable
class FeesPort(Protocol):
    """Single auditable fee ledger. Owned by M07 fees."""

    def raise_charge(
        self,
        context: RequestContext,
        source_key: str,
        student_id: UUID,
        fee_head_id: UUID,
        amount_paise: int,
        due_date: date,
        description_key: str,
    ) -> ChargeDTO:
        """Post a charge keyed by school-unique source_key.

        Identical source_key + payload returns the existing charge. Changed
        payload on the same key raises StateConflict (409).
        """
        ...

    def credit_charge(
        self,
        context: RequestContext,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
    ) -> CreditDTO:
        """Post an approved concession/credit against one charge."""
        ...

    def get_balance(
        self,
        context: RequestContext,
        student_id: UUID,
        as_of: date | None = None,
    ) -> BalanceDTO:
        """Return ledger totals for one student as of a school civil date."""
        ...
