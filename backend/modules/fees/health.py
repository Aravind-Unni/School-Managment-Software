"""Readiness probe for fees tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when FeeHead table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM fees_feehead LIMIT 1")
    return True
