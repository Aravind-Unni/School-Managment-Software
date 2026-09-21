"""The module-local DomainExchangePort and the shared pieces every adapter uses.

Deliberately NOT in ``backend/contracts``: a shared Protocol would invite other
modules to register adapters into M13's registry, and the frozen packet places
this registry inside the module (review-decisions item 4).

Every adapter in this package is a DETERMINISTIC FAKE standing in for the real
domain write path, which review-decisions item 16 records as PENDING. Each
records its calls so a test can assert what the exchange actually asked for,
and each refuses an operation it does not own rather than silently succeeding.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Protocol, runtime_checkable

from contracts.identity import RequestContext

#: Row error codes this package emits. Data, not branches: an adapter names one
#: of these rather than inventing a string at the call site.
CODE_MALFORMED_ROW = "malformed_row"
CODE_MISSING_VALUE = "missing_value"
CODE_INVALID_UUID = "invalid_uuid"
CODE_INVALID_DATE = "invalid_date"
CODE_INVALID_AMOUNT = "invalid_amount"
CODE_INVALID_MARKS = "invalid_marks"
CODE_DUPLICATE_ROW = "duplicate_row"
CODE_UNKNOWN_COLUMN = "unknown_column"


def is_uuid(value: str) -> bool:
    """Return whether a cell parses as a UUID."""
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return True


def is_iso_date(value: str) -> bool:
    """Return whether a cell parses as an ISO-8601 civil date."""
    try:
        datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        return False
    return True


def is_paise(value: str) -> bool:
    """Return whether a cell is a non-negative integer number of paise.

    Integer paise only: the foundation forbids float money, so a cell with a
    decimal point is rejected rather than rounded.
    """
    return value.isdigit()


def is_marks(value: str) -> bool:
    """Return whether a cell is a decimal-string mark with at most two places."""
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return False
    return parsed >= 0 and -parsed.as_tuple().exponent <= 2


class ExplicitlyUnused(RuntimeError):
    """Raised when exchange code reaches a domain operation it must never use.

    FeesPort ``raise``/``credit`` is the case the packet names (item 14):
    rendering a fee line on a report reads a balance, it never posts to the
    ledger. Raising beats returning a plausible value, because a silent success
    is how a reporting bug becomes an accounting one.
    """


@dataclass(frozen=True, slots=True)
class RowError:
    """One row-scoped problem, in the frozen DomainRowError shape."""

    row: int
    field: str
    code: str

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted DomainRowError shape."""
        return {"row": self.row, "field": self.field, "code": self.code}


def validate_result(accepted: int, errors: list[RowError]) -> dict:
    """Return the frozen DomainValidateResult shape."""
    return {"accepted": accepted, "errors": [error.to_wire() for error in errors]}


def apply_result(applied: int, errors: list[RowError]) -> dict:
    """Return the frozen DomainApplyResult shape."""
    return {"applied": applied, "errors": [error.to_wire() for error in errors]}


def export_page(schema_version: str, rows: list[dict], next_cursor: str | None = None) -> dict:
    """Return the frozen DomainExportPage shape."""
    return {"schema_version": schema_version, "rows": rows, "next_cursor": next_cursor}


@dataclass(frozen=True, slots=True)
class ExportPorts:
    """The service ports an export adapter is allowed to read.

    Named explicitly rather than handed the whole registry, so an adapter
    cannot quietly grow a dependency the module never declared. There is no
    performance port here: M06 is not an M13 consumer, so the progress and
    at-risk adapters synthesise their rows from roster and attendance facts.
    """

    registry: object = None
    attendance: object = None
    assessment: object = None
    fees: object = None
    clock: object = None


@runtime_checkable
class DomainExchangePort(Protocol):
    """Validate, apply and page rows for one dataset family."""

    def validate_rows(self, ctx: RequestContext, rows: list[dict]) -> dict:
        """Return ``{accepted, errors}`` without writing anything.

        ``rows`` are neutralised source rows shaped
        ``{"number": int, "values": {column: str}, "malformed": bool}``.
        """
        ...

    def apply_rows(self, ctx: RequestContext, batch_key: str, rows: list[dict]) -> dict:
        """Apply one batch and return ``{applied, errors}``. Idempotent on batch_key."""
        ...

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Return one page of export rows for the dataset."""
        ...


@dataclass
class AdapterBase:
    """Shared call recording and refusals for every dataset adapter.

    Subclasses override only the direction they own; the other direction raises
    NotImplementedError naming the dataset, so a registry mis-wire fails loudly
    instead of exporting an empty file.
    """

    dataset: str = ""
    schema_version: str = ""
    template_version: str = ""
    columns: tuple[str, ...] = ()
    key_columns: tuple[str, ...] = ()
    export_fields: tuple[str, ...] = ()
    forbidden_fields: tuple[str, ...] = ()
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    #: batch_key -> applied count, so a replayed batch returns its first answer.
    applied_batches: dict[str, int] = field(default_factory=dict)

    def record(self, name: str, *args, **kwargs) -> None:
        """Append one call record for test assertions."""
        self.calls.append((name, args, kwargs))

    def validate_rows(self, ctx: RequestContext, rows: list[dict]) -> dict:
        """Refuse: this adapter does not own an import direction."""
        raise NotImplementedError(f"{self.dataset!r} is not an import dataset")

    def apply_rows(self, ctx: RequestContext, batch_key: str, rows: list[dict]) -> dict:
        """Refuse: this adapter does not own an import direction."""
        raise NotImplementedError(f"{self.dataset!r} is not an import dataset")

    def export_rows(
        self,
        ctx: RequestContext,
        dataset: str,
        filters: dict,
        cursor: str | None,
    ) -> dict:
        """Refuse: this adapter does not own an export direction."""
        raise NotImplementedError(f"{self.dataset!r} is not an export dataset")

    def granted_fields(self, requested: list[str]) -> list[str]:
        """Return the requested fields this dataset permits, in request order.

        A field that is unknown to the dataset, or named in
        ``forbidden_fields``, is OMITTED rather than rejected: the reviewer gets
        the columns they may have, and the export job records the difference.
        """
        allowed = set(self.export_fields) - set(self.forbidden_fields)
        return [name for name in requested if name in allowed]
