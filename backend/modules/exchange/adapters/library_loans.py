"""Deterministic library-loans import adapter, standing in for M09's writes.

No fines are computed or imported: M09's review recorded that this product has
no fine policy, and a bulk import is not the place to invent one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts.identity import RequestContext

from .base import (
    CODE_INVALID_DATE,
    CODE_INVALID_UUID,
    CODE_MALFORMED_ROW,
    CODE_MISSING_VALUE,
    AdapterBase,
    RowError,
    apply_result,
    is_iso_date,
    is_uuid,
    validate_result,
)


@dataclass
class LibraryLoansAdapter(AdapterBase):
    """Validates ``copy_id, borrower_id, issued_on, due_on`` rows."""

    dataset: str = "library_loans"
    schema_version: str = "library-loans-schema-v1"
    template_version: str = "library-loans-v1"
    columns: tuple[str, ...] = ("copy_id", "borrower_id", "issued_on", "due_on")
    key_columns: tuple[str, ...] = ("copy_id",)
    #: copy_id -> borrower_id, the open loan a real M09 apply would have created.
    loans: dict[str, str] = field(default_factory=dict)

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
        """Record one batch of open loans, idempotently on batch_key."""
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
            self.loans[values["copy_id"]] = values["borrower_id"]
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
        for column in ("copy_id", "borrower_id"):
            cell = values.get(column, "")
            if not cell:
                found.append(RowError(number, column, CODE_MISSING_VALUE))
            elif not is_uuid(cell):
                found.append(RowError(number, column, CODE_INVALID_UUID))
        for column in ("issued_on", "due_on"):
            cell = values.get(column, "")
            if not cell:
                found.append(RowError(number, column, CODE_MISSING_VALUE))
            elif not is_iso_date(cell):
                found.append(RowError(number, column, CODE_INVALID_DATE))
        return found
