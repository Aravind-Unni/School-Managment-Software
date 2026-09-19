"""Health checks contributed by the demo module."""

from __future__ import annotations


def check_table() -> dict[str, object]:
    """Return whether the demo table is queryable.

    Used by /readyz. Returns a dict rather than raising so that one failing
    check does not hide the others.
    """
    from .models import DemoNote

    try:
        DemoNote.objects.exists()
    except Exception as exc:
        return {"name": "demo_table", "ok": False, "detail": type(exc).__name__}
    return {"name": "demo_table", "ok": True}
