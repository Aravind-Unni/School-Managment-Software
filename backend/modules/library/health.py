"""Readiness probe for library tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when Title table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM library_title LIMIT 1")
    return True
