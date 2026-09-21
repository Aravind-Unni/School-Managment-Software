"""Readiness probe for exchange tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when the ImportJob table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM exchange_import_job LIMIT 1")
    return True
