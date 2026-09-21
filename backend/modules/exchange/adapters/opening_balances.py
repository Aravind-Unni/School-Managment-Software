"""Deterministic opening-balances import adapter, standing in for M07's writes.

Opening balances are ledger charges (M07 review-decisions), so this adapter
accepts integer paise only and never a rupee decimal. It records the charges it
would have posted; it does NOT call FeesPort.raise_charge, because exchange code
posting to the ledger is exactly what item 14 forbids.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts.identity import RequestContext

from .base import (
    CODE_INVALID_AMOUNT,
    CODE_INVALID_DATE,
    CODE_INVALID_UUID,
    CODE_MALFORMED_ROW,
    CODE_MISSING_VALUE,
    AdapterBase,
    RowError,
    apply_result,
    is_iso_date,
    is_paise,
    is_uuid,
    validate_result,
)


@dataclass
class OpeningBalancesAdapter(AdapterBase):
    """Validates ``student_id, fee_head_id, amount_paise, due_date`` rows."""

    dataset: str = "opening_balances"
    schema_version: str = "opening-balances-schema-v1"
    template_version: str = "opening-balances-v1"
    columns: tuple[str, ...] = ("student_id", "fee_head_id", "amount_paise", "due_date")
    key_columns: tuple[str, ...] = ("student_id", "fee_head_id")
    #: (student_id, fee_head_id) -> paise, the state a real M07 apply would write.
    balances: dict[tuple[str, str], int] = field(default_factory=dict)

    def validate_rows(self, ctx: RequestContext, rows: list[dict]) -> dict:
        """Check grammar and return accepted count plus row errors."""
        self.record("validate_rows", count=len(rows))
        errors: list[RowError] = []
        accepted = 0
        for row in rows:
            row_errors = self._row_errors(row)
            errors.extend(row_errors)
            if not row_errors:
                accepted += 1
        return validate_result(accepted, errors)

    def apply_rows(self, ctx: RequestContext, batch_key: str, rows: list[dict]) -> dict:
        """Record one batch of opening balances, idempotently on batch_key."""
        self.record("apply_rows", batch_key=batch_key, count=len(rows))
        if batch_key in self.applied_batches:
            return apply_result(self.applied_batches[batch_key], [])
        applied = 0
        errors: list[RowError] = []
        for row in rows:
            row_errors = self._row_errors(row)
            if row_errors:
                errors.extend(row_errors)
                continue
            values = row["values"]
            key = (values["student_id"], values["fee_head_id"])
            self.balances[key] = int(values["amount_paise"])
            applied += 1
        self.applied_batches[batch_key] = applied
        return apply_result(applied, errors)

    def _row_errors(self, row: dict) -> list[RowError]:
        """Return every grammar problem in one row, in column order."""
        number = row["number"]
        if row.get("malformed"):
            return [RowError(number, "row", CODE_MALFORMED_ROW)]
        values = row["values"]
        found: list[RowError] = []
        for column in ("student_id", "fee_head_id"):
            cell = values.get(column, "")
            if not cell:
                found.append(RowError(number, column, CODE_MISSING_VALUE))
            elif not is_uuid(cell):
                found.append(RowError(number, column, CODE_INVALID_UUID))
        amount = values.get("amount_paise", "")
        if not amount:
            found.append(RowError(number, "amount_paise", CODE_MISSING_VALUE))
        elif not is_paise(amount) or int(amount) < 1:
            found.append(RowError(number, "amount_paise", CODE_INVALID_AMOUNT))
        due_date = values.get("due_date", "")
        if due_date and not is_iso_date(due_date):
            found.append(RowError(number, "due_date", CODE_INVALID_DATE))
        return found
