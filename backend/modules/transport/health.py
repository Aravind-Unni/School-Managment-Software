"""Readiness probe for transport tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when Bus table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM transport_bus LIMIT 1")
    return True
