"""Readiness probe for assessment tables."""

from __future__ import annotations


def tables_ready() -> dict[str, object]:
    """Return whether the assessment table is queryable."""
    from .models import Assessment

    try:
        Assessment.objects.exists()
    except Exception as exc:
        return {"name": "assessment_tables", "ok": False, "detail": type(exc).__name__}
    return {"name": "assessment_tables", "ok": True}
