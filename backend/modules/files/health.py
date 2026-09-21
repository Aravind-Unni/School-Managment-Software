"""Readiness probe for files tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when File table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM files_file LIMIT 1")
    return True
