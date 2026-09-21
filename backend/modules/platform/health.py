"""Readiness probe for platform tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when platform audit table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM platform_audit_record LIMIT 1")
    return True
