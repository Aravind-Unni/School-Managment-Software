"""Keyset paging for the one M13 collection endpoint that has a cursor.

Keyset rather than offset, as the foundation requires: an error list is read
while a reviewer is fixing the file, so rows move and an offset would skip
some of them.
"""

from __future__ import annotations

from contracts.errors import ValidationFailed
from contracts.pagination import DEFAULT_PAGE_SIZE, decode_cursor, encode_cursor

from ..models import ImportJob, ImportRow
from .wire import import_row_errors


def page_of_errors(job: ImportJob, cursor: str | None) -> dict:
    """Return one page of row errors, ordered by source row number.

    The cursor carries the last row number seen, so a reviewer who re-reads
    page two after fixing page one gets the errors that are still there rather
    than a shifted window.

    Raises ValidationFailed carrying ``error.malformed_cursor`` for a
    hand-edited cursor, which is a 422 at the boundary and not a 500 inside.
    """
    after = 0
    if cursor:
        try:
            position = decode_cursor(cursor)
        except ValueError as exc:
            raise ValidationFailed("error.malformed_cursor") from exc
        if "row" not in position:
            raise ValidationFailed("error.cursor_field_missing")
        after = int(position["row"])

    rows = list(
        ImportRow.objects.filter(job_id=job.id, number__gt=after)
        .exclude(validation_errors=[])
        .order_by("number")[: DEFAULT_PAGE_SIZE + 1]
    )
    has_more = len(rows) > DEFAULT_PAGE_SIZE
    visible = rows[:DEFAULT_PAGE_SIZE]
    items: list[dict] = []
    for row in visible:
        items.extend(import_row_errors(row))
    next_cursor = encode_cursor({"row": visible[-1].number}) if has_more and visible else None
    return {"items": items, "next_cursor": next_cursor}
