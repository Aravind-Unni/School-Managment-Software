"""Query-parameter parsing and paging for M03's collections.

A malformed parameter is a 422 naming the field, never an ignored value. Ignoring
one would answer a different question from the one the caller asked -- a date
filter silently dropped returns every date, which reads as data rather than as an
error.

Page sizes are refused rather than clamped, for the same reason: a caller that
asked for 500 and silently got 200 will page wrongly and never find out.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from contracts.errors import FieldError, ValidationFailed

#: Frozen in contracts/M03/openapi.json.
DEFAULT_PAGE_SIZE = 50
MAXIMUM_PAGE_SIZE = 200


def _invalid(name: str) -> ValidationFailed:
    """Return the 422 for a malformed query parameter."""
    return ValidationFailed(
        "error.validation_failed",
        field_errors=(FieldError(name, "error.field_not_accepted"),),
    )


def optional_uuid(request, name: str) -> UUID | None:
    """Return a UUID query parameter, or None when absent."""
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise _invalid(name) from exc


def required_uuid(request, name: str) -> UUID:
    """Return a UUID query parameter, refusing an absent one."""
    value = optional_uuid(request, name)
    if value is None:
        raise _invalid(name)
    return value


def optional_date(request, name: str) -> date | None:
    """Return an ISO date query parameter, or None when absent."""
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise _invalid(name) from exc


def required_date(request, name: str) -> date:
    """Return an ISO date query parameter, refusing an absent one."""
    value = optional_date(request, name)
    if value is None:
        raise _invalid(name)
    return value


def optional_choice(request, name: str, allowed: tuple[str, ...]) -> str | None:
    """Return an enumerated query parameter, refusing a value outside the set."""
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    if raw not in allowed:
        raise _invalid(name)
    return raw


def page_size(request) -> int:
    """Return the requested page size, refusing anything out of range."""
    raw = request.query_params.get("page_size")
    if raw is None or raw == "":
        return DEFAULT_PAGE_SIZE
    try:
        requested = int(raw)
    except ValueError as exc:
        raise _invalid("page_size") from exc
    if requested < 1 or requested > MAXIMUM_PAGE_SIZE:
        raise _invalid("page_size")
    return requested


def paginate(request, queryset, *, order_by, cursor_fields, serialise):
    """Return one keyset page in the frozen {items, next_cursor} shape.

    Delegates to the shared helper so the cursor format, the malformed-cursor 422
    and the page shape are the foundation's and not this module's invention.
    """
    from shared.http.pagination import paginate_queryset

    page = paginate_queryset(
        queryset,
        cursor=request.query_params.get("cursor") or None,
        page_size=page_size(request),
        order_by=order_by,
        cursor_fields=cursor_fields,
    )
    return page.to_wire(serialise)
