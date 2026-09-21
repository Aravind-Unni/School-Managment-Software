"""Deterministic results import adapter, standing in for M05's write path.

Marks arrive as decimal strings, never floats, matching the foundation rule. No
grade letter is derived here: CBSE grade boundaries are school policy this
project has not been given, and inventing one is forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts.identity import RequestContext

from .base import (
    CODE_INVALID_MARKS,
    CODE_INVALID_UUID,
    CODE_MALFORMED_ROW,
    CODE_MISSING_VALUE,
    AdapterBase,
    RowError,
    apply_result,
    is_marks,
    is_uuid,
    validate_result,
)


@dataclass
class ResultsAdapter(AdapterBase):
    """Validates ``student_id, assessment_id, marks_obtained`` rows."""

    dataset: str = "results"
    schema_version: str = "results-schema-v1"
    template_version: str = "results-v1"
    columns: tuple[str, ...] = ("student_id", "assessment_id", "marks_obtained")
    key_columns: tuple[str, ...] = ("student_id", "assessment_id")
    #: (student_id, assessment_id) -> marks string a real M05 apply would write.
    marks: dict[tuple[str, str], str] = field(default_factory=dict)

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
        """Record one batch of marks, idempotently on batch_key."""
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
            self.marks[(values["student_id"], values["assessment_id"])] = values[
                "marks_obtained"
            ]
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
        for column in ("student_id", "assessment_id"):
            cell = values.get(column, "")
            if not cell:
                found.append(RowError(number, column, CODE_MISSING_VALUE))
            elif not is_uuid(cell):
                found.append(RowError(number, column, CODE_INVALID_UUID))
        obtained = values.get("marks_obtained", "")
        if not obtained:
            found.append(RowError(number, "marks_obtained", CODE_MISSING_VALUE))
        elif not is_marks(obtained):
            found.append(RowError(number, "marks_obtained", CODE_INVALID_MARKS))
        return found
