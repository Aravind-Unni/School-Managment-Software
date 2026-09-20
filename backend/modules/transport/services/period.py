"""Period calendar helpers for billing eligibility. Pure — no IO."""

from __future__ import annotations

import calendar
from datetime import date


def parse_period(period: str) -> tuple[int, int]:
    """Parse YYYY-MM into (year, month). Assumes the OpenAPI pattern already matched."""
    year_s, month_s = period.split("-", 1)
    return int(year_s), int(month_s)


def period_bounds(period: str) -> tuple[date, date]:
    """Return inclusive first and last civil dates of YYYY-MM."""
    year, month = parse_period(period)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def covers_full_period(
    *,
    from_date: date,
    to_date: date | None,
    period: str,
) -> bool:
    """Return True when the participation covers every day of the period."""
    start, end = period_bounds(period)
    if from_date > start:
        return False
    if to_date is not None and to_date < end:
        return False
    return True


def overlaps_period(
    *,
    from_date: date,
    to_date: date | None,
    period: str,
) -> bool:
    """Return True when the participation intersects the period at all."""
    start, end = period_bounds(period)
    if from_date > end:
        return False
    if to_date is not None and to_date < start:
        return False
    return True


def ranges_overlap(
    a_from: date,
    a_to: date | None,
    b_from: date,
    b_to: date | None,
) -> bool:
    """Return True when two half-open-to-closed date ranges overlap.

    Open-ended ``to_date`` (None) means ongoing. Does not invent school holidays.
    """
    a_end = a_to or date.max
    b_end = b_to or date.max
    return a_from <= b_end and b_from <= a_end


def source_key_for(participation_id, period: str, charge_kind: str = "period") -> str:
    """Build the Fees source_key for one participation/period/kind."""
    return f"transport:{participation_id}:{period}:{charge_kind}"
