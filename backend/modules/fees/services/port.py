"""In-process FeesPort implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from contracts.fees import BalanceDTO, ChargeDTO, CreditDTO
from contracts.identity import RequestContext

from .authority import AuthorityGate
from .charges import ChargeService
from .corrections import CorrectionService
from .statements import StatementService


@dataclass(frozen=True, slots=True)
class FeesService:
    """Concrete FeesPort for in-process consumers."""

    charges: ChargeService
    corrections: CorrectionService
    statements: StatementService
    gate: AuthorityGate

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
        """Post or replay a charge by source_key."""
        dto, _ = self.charges.raise_charge(
            context,
            source_key=source_key,
            student_id=student_id,
            fee_head_id=fee_head_id,
            amount_paise=amount_paise,
            due_date=due_date,
            description_key=description_key,
        )
        return dto

    def credit_charge(
        self,
        context: RequestContext,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
    ) -> CreditDTO:
        """Post a concession credit."""
        return self.corrections.credit_charge_port(
            context, charge_id, amount_paise, reason, source_key
        )

    def get_balance(
        self,
        context: RequestContext,
        student_id: UUID,
        as_of: date | None = None,
    ) -> BalanceDTO:
        """Return derived balance totals."""
        return self.statements.get_balance(context, student_id, as_of)
