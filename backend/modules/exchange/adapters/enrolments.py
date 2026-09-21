"""Deterministic enrolments import adapter, standing in for M02's write path.

Real M02 adapters are PENDING (review-decisions item 16). This adapter validates
the column grammar and records what it would have applied, which is enough to
prove the exchange's own guarantees: duplicate detection, formula neutralisation
and idempotent resume.
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
class EnrolmentsAdapter(AdapterBase):
    """Validates and applies ``student_id, section_id, effective_from`` rows."""

    dataset: str = "enrolments"
    schema_version: str = "enrolments-schema-v1"
    template_version: str = "enrolments-v1"
    columns: tuple[str, ...] = ("student_id", "section_id", "effective_from")
    key_columns: tuple[str, ...] = ("student_id", "section_id", "effective_from")
    #: student_id -> section_id, the state a real M02 apply would have written.
    placements: dict[str, str] = field(default_factory=dict)

    def validate_rows(self, ctx: RequestContext, rows: list[dict]) -> dict:
        """Check each row's grammar and return accepted count plus row errors.

        Does not handle: duplicate detection across the file. That is the
        exchange's job, because the key columns are declared here but the
        whole-file view belongs to the import service.
        """
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
        """Apply one batch of enrolment placements, idempotently on batch_key.

        A replayed batch_key returns the count recorded the first time and
        writes nothing further, which is what makes a resumed commit safe.
        """
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
            self.placements[values["student_id"]] = values["section_id"]
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
        for column in ("student_id", "section_id"):
            cell = values.get(column, "")
            if not cell:
                found.append(RowError(number, column, CODE_MISSING_VALUE))
            elif not is_uuid(cell):
                found.append(RowError(number, column, CODE_INVALID_UUID))
        effective_from = values.get("effective_from", "")
        if not effective_from:
            found.append(RowError(number, "effective_from", CODE_MISSING_VALUE))
        elif not is_iso_date(effective_from):
            found.append(RowError(number, "effective_from", CODE_INVALID_DATE))
        return found
