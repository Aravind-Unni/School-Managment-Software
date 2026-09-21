"""Keyset-paged reads of Registry reference data and people.

One function for every collection a picker or directory needs, so each list
is authorised, school-scoped and paged the same way. Ordered by id: stable
under renames, so a cursor never skips or repeats a row.
Does not handle: ordering by name (callers sort a page, pickers load all).
"""

from __future__ import annotations

from uuid import UUID

from django.db.models import Q

from contracts.identity import RequestContext
from contracts.scope import ScopeFacts


def list_page(
    context: RequestContext,
    access,
    model,
    *,
    action: str,
    after_id: UUID | None,
    page_size: int,
    query: str | None = None,
    search_fields: tuple[str, ...] = (),
) -> tuple[tuple, bool]:
    """Return (rows, has_more) for one page of ``model`` in the caller's school.

    ``action`` is checked school-wide before anything is read. ``query``
    filters case-insensitively across ``search_fields`` before paging.
    """
    access.check(context, action, ScopeFacts(resource_school_id=context.school_id))
    queryset = model.objects.filter(school_id=context.school_id).order_by("id")
    needle = (query or "").strip()
    if needle and search_fields:
        condition = Q()
        for name in search_fields:
            condition |= Q(**{f"{name}__icontains": needle})
        queryset = queryset.filter(condition)
    if after_id is not None:
        queryset = queryset.filter(id__gt=after_id)
    rows = tuple(queryset[: page_size + 1])
    return rows[:page_size], len(rows) > page_size
