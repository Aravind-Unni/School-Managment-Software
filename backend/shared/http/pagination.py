"""Keyset pagination helper shared by every list endpoint.

Enforces the ``{items, next_cursor}`` shape and the page-size ceiling so a
module cannot ship an unbounded list over a 4,000-student roster.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from contracts.errors import FieldError, ValidationFailed
from contracts.pagination import Page, clamp_page_size, decode_cursor, encode_cursor


def paginate_queryset[RowT](
    queryset: Iterable[RowT],
    *,
    cursor: str | None,
    page_size: int | None,
    order_by: Sequence[str],
    cursor_fields: Callable[[RowT], dict[str, object]],
) -> Page[RowT]:
    """Return one keyset page from an ordered queryset.

    ``order_by`` must end in a unique tiebreaker (usually ``"id"``), otherwise
    rows with equal sort keys can be skipped or repeated across pages.
    ``cursor_fields`` extracts the position of the last row for the next cursor.

    Raises ValidationFailed (422) on a malformed cursor. Translating it here,
    rather than leaving the primitive's ValueError to escape, is what stops a
    hand-edited cursor from becoming a 500 in every module that paginates.

    Does not handle: backwards paging. Only forward paging is supported, because
    the UI never needs to walk backwards and a reverse cursor doubles the
    correctness surface.
    """
    if not order_by:
        raise ValueError("order_by must name at least one field")

    size = clamp_page_size(page_size)
    rows = list(queryset)

    if cursor is not None:
        try:
            position = decode_cursor(cursor)
        except ValueError as exc:
            raise ValidationFailed(
                "error.malformed_cursor",
                field_errors=(FieldError("cursor", "error.malformed_cursor"),),
            ) from exc
        try:
            rows = [row for row in rows if _is_after(cursor_fields(row), position, order_by)]
        except KeyError as exc:
            # The cursor decoded but does not carry this collection's sort keys,
            # which means it was forged or belongs to a different endpoint.
            raise ValidationFailed(
                "error.malformed_cursor",
                field_errors=(FieldError("cursor", "error.cursor_field_missing"),),
            ) from exc

    window = rows[: size + 1]
    has_more = len(window) > size
    items = tuple(window[:size])
    next_cursor = encode_cursor(cursor_fields(items[-1])) if has_more and items else None
    return Page(items=items, next_cursor=next_cursor)


def _is_after(
    row_position: dict[str, object],
    cursor_position: dict[str, object],
    order_by: Sequence[str],
) -> bool:
    """Return whether a row sorts strictly after the cursor position.

    Compares fields in ``order_by`` order, honouring a leading '-' for descending.
    Assumes every ordering field is present in both dicts and mutually
    comparable; a mismatch raises TypeError rather than silently ordering wrong.
    """
    for field in order_by:
        descending = field.startswith("-")
        name = field.lstrip("-")
        row_value = row_position[name]
        cursor_value = cursor_position[name]
        if row_value == cursor_value:
            continue
        ahead = row_value < cursor_value if descending else row_value > cursor_value  # type: ignore[operator]
        return bool(ahead)
    return False
