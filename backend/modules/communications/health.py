"""Readiness probe for communications tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when Notice table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM communications_notice LIMIT 1")
    return True
