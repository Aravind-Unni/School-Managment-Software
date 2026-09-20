"""In-memory FakeFees implementing FeesPort for M08 standalone and tests.

Source_key dedupe mirrors the real ledger: identical payload returns the same
charge; a changed payload raises StateConflict. ``arm_timeout_after_commit``
commits then raises FeesCommitTimeout so transport can exercise lost-link
recovery without a real broker timeout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.fees import BalanceDTO, ChargeDTO, CreditDTO
from contracts.identity import RequestContext

from .failures import FailureInjector


class FeesCommitTimeout(RuntimeError):
    """Raised after a charge is committed when a timeout was armed for its key.

    The charge remains stored. A retry with the same source_key returns it.
    """


@dataclass(frozen=True, slots=True)
class FeePlanSeed:
    """Approved fee-plan reference FakeFees hands to transport billing."""

    fee_plan_id: UUID
    fee_head_id: UUID
    amount_paise: int
    proration_policy: str | None


@dataclass
class FakeFees:
    """Dictionary-backed FeesPort with commit-then-timeout and plan seeds."""

    failures: FailureInjector = field(default_factory=FailureInjector)
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    _plans: dict[UUID, FeePlanSeed] = field(default_factory=dict)
    _charges_by_key: dict[str, ChargeDTO] = field(default_factory=dict)
    _charges_by_id: dict[UUID, ChargeDTO] = field(default_factory=dict)
    _payloads: dict[str, dict[str, object]] = field(default_factory=dict)
    _credits: list[CreditDTO] = field(default_factory=list)
    _timeout_keys: set[str] = field(default_factory=set)

    def seed_plan(
        self,
        *,
        fee_plan_id: UUID,
        fee_head_id: UUID,
        amount_paise: int,
        proration_policy: str | None,
    ) -> FeePlanSeed:
        """Install one approved fee-plan amount reference for billing."""
        if amount_paise < 1:
            raise ValidationFailed("error.validation_failed")
        plan = FeePlanSeed(
            fee_plan_id=fee_plan_id,
            fee_head_id=fee_head_id,
            amount_paise=amount_paise,
            proration_policy=proration_policy,
        )
        self._plans[fee_plan_id] = plan
        return plan

    def get_plan(self, fee_plan_id: UUID) -> FeePlanSeed:
        """Return a seeded plan, or raise ValidationFailed when unknown."""
        plan = self._plans.get(fee_plan_id)
        if plan is None:
            raise ValidationFailed("transport.error.fee_plan_missing")
        return plan

    def arm_timeout_after_commit(self, source_key: str) -> None:
        """Arm a one-shot timeout: next raise_charge for key commits then raises."""
        self._timeout_keys.add(source_key)

    def list_charges(self) -> list[ChargeDTO]:
        """Return every stored charge in insertion order."""
        return list(self._charges_by_id.values())

    def get_by_source_key(self, source_key: str) -> ChargeDTO | None:
        """Return the charge for ``source_key``, or None when absent."""
        return self._charges_by_key.get(source_key)

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
        payload on the same key raises StateConflict. When the key was armed
        for timeout, the charge is committed then FeesCommitTimeout is raised.
        """
        self.calls.append(
            (
                "raise_charge",
                (source_key, student_id, fee_head_id, amount_paise, due_date, description_key),
                {},
            )
        )
        self.failures.maybe_fail("fees.raise_charge")
        if amount_paise < 1:
            raise ValidationFailed("error.validation_failed")
        payload = {
            "student_id": str(student_id),
            "fee_head_id": str(fee_head_id),
            "amount_paise": amount_paise,
            "due_date": due_date.isoformat(),
            "description_key": description_key,
            "school_id": str(context.school_id),
        }
        existing = self._charges_by_key.get(source_key)
        if existing is not None:
            if self._payloads[source_key] != payload:
                raise StateConflict("fees.error.source_key_conflict")
            return existing
        charge = ChargeDTO(
            id=uuid4(),
            source_key=source_key,
            amount_paise=amount_paise,
            balance_paise=amount_paise,
            status="open",
            student_id=student_id,
            fee_head_id=fee_head_id,
            due_date=due_date,
            school_id=context.school_id,
            description_key=description_key,
            version=1,
        )
        self._charges_by_key[source_key] = charge
        self._charges_by_id[charge.id] = charge
        self._payloads[source_key] = payload
        if source_key in self._timeout_keys:
            self._timeout_keys.discard(source_key)
            raise FeesCommitTimeout(f"fees commit timed out after posting {source_key}")
        return charge

    def credit_charge(
        self,
        context: RequestContext,
        charge_id: UUID,
        amount_paise: int,
        reason: str,
        source_key: str,
    ) -> CreditDTO:
        """Post an adjustment credit against one stored charge."""
        self.calls.append(("credit_charge", (charge_id, amount_paise, reason, source_key), {}))
        self.failures.maybe_fail("fees.credit_charge")
        charge = self._charges_by_id.get(charge_id)
        if charge is None or charge.school_id != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        if amount_paise < 1 or not reason.strip():
            raise ValidationFailed("error.validation_failed")
        for prior in self._credits:
            if prior.source_key == source_key:
                return prior
        new_balance = max(0, charge.balance_paise - amount_paise)
        if new_balance == 0:
            status = "credited"
        elif new_balance < charge.amount_paise:
            status = "partial"
        else:
            status = "open"
        updated = ChargeDTO(
            id=charge.id,
            source_key=charge.source_key,
            amount_paise=charge.amount_paise,
            balance_paise=new_balance,
            status=status,
            student_id=charge.student_id,
            fee_head_id=charge.fee_head_id,
            due_date=charge.due_date,
            school_id=charge.school_id,
            description_key=charge.description_key,
            version=charge.version,
        )
        self._charges_by_id[charge.id] = updated
        self._charges_by_key[charge.source_key] = updated
        credit = CreditDTO(
            id=uuid4(),
            charge_id=charge_id,
            amount_paise=amount_paise,
            reason=reason,
            source_key=source_key,
            student_id=charge.student_id,
            kind="adjustment",
        )
        self._credits.append(credit)
        return credit

    def get_balance(
        self,
        context: RequestContext,
        student_id: UUID,
        as_of: date | None = None,
    ) -> BalanceDTO:
        """Return ledger totals for one student from stored charges/credits."""
        self.calls.append(("get_balance", (student_id, as_of), {}))
        self.failures.maybe_fail("fees.get_balance")
        on = as_of or date(1970, 1, 1)
        charges = [
            c
            for c in self._charges_by_id.values()
            if c.student_id == student_id and c.school_id == context.school_id
        ]
        credit_rows = [
            c for c in self._credits if c.student_id == student_id and c.charge_id is not None
        ]
        charged = sum(c.amount_paise for c in charges)
        outstanding = sum(c.balance_paise for c in charges)
        credited = sum(c.amount_paise for c in credit_rows)
        overdue = sum(
            c.balance_paise
            for c in charges
            if c.due_date is not None and c.due_date <= on and c.balance_paise > 0
        )
        return BalanceDTO(
            student_id=student_id,
            charged_paise=charged,
            credited_paise=credited,
            paid_paise=0,
            outstanding_paise=outstanding,
            overdue_paise=overdue,
            credit_available_paise=0,
            as_of=on,
        )
