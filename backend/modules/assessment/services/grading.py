"""Grade letters from the school's grade bands.

The bands come from the school config file (``[[grading.bands]]``, highest
first, the last starting at 0) and are installed into the school's settings.
A score gets the first band whose ``min_percent`` its percentage reaches.
``grade_for`` is pure; ``school_bands`` reads the installed settings.

Does not handle: grades for absent pupils or ungraded (null) scores, which
stay without a grade, or different bands per standard.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def grade_for(score, max_score, bands: list[dict] | None) -> str | None:
    """Return the grade letter for score/max_score, or None when not gradable."""
    if not bands or score is None or max_score is None:
        return None
    try:
        maximum = Decimal(str(max_score))
        percent = Decimal(str(score)) * 100 / maximum
    except (InvalidOperation, ZeroDivisionError):
        return None
    if maximum <= 0:
        return None
    for band in bands:
        if percent >= Decimal(str(band.get("min_percent", 0))):
            return str(band.get("grade"))
    return None


def school_bands(registry, context) -> list[dict]:
    """Return the school's installed grade bands, highest first (empty if none)."""
    profile_of = getattr(registry, "school_profile", None)
    profile = profile_of(context) if profile_of is not None else None
    if profile is None:
        return []
    return list((profile.settings or {}).get("grading_bands") or [])
