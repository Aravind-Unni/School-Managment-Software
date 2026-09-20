"""Readiness probe for attendance tables."""

from __future__ import annotations


def tables_ready() -> bool:
    """Return True when the attendance session table is queryable."""
    from .models import AttendanceSession

    AttendanceSession.objects.exists()
    return True
