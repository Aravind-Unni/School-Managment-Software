"""Shared GET handler for Registry collections: page, authorise, render.

Kept out of views.py so each collection's ``get`` stays a single call.
"""

from __future__ import annotations

from collections.abc import Callable

from rest_framework.request import Request
from rest_framework.response import Response

from ..services.listing import list_page
from .cursors import decode_cursor, encode_cursor, resolve_page_size
from .deps import people_service


def list_response(
    request: Request,
    model,
    to_wire: Callable,
    *,
    action: str,
    with_external_ids: bool = False,
    search_fields: tuple[str, ...] = (),
) -> Response:
    """Return one page of ``model`` rows as ``{items, next_cursor}``."""
    service = people_service()
    rows, has_more = list_page(
        request.school_context,
        service.access,
        model,
        action=action,
        after_id=decode_cursor(request.query_params.get("cursor")),
        page_size=resolve_page_size(request.query_params.get("page_size")),
        query=request.query_params.get("query") if search_fields else None,
        search_fields=search_fields,
    )
    items = [
        to_wire(row, service.external_ids_for(row.id)) if with_external_ids else to_wire(row)
        for row in rows
    ]
    return Response(
        {
            "items": items,
            "next_cursor": encode_cursor(rows[-1].id) if has_more and rows else None,
        }
    )
