"""Readiness probe for performance tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when MetricDefinition table is queryable."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM performance_metricdefinition LIMIT 1")
    return True
