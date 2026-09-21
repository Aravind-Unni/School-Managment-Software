"""Inclusive date-range helpers for M02's dated links and enrolments.

Every range in this module treats both endpoints as inclusive, matching how a
school states a posting or a term. Callers pass school-local dates, not UTC
midnights derived from a clock elsewhere.

Does not handle: calendar exceptions or holidays. Those belong to modules that
own the calendar, not to membership overlap checks.
"""

from __future__ import annotations

from datetime import date, timedelta


def range_covers(*, from_date: date, to_date: date | None, effective_date: date) -> bool:
    """Return whether ``effective_date`` falls inside an inclusive range.

    A null ``to_date`` means open-ended from ``from_date`` onward.
    """
    if effective_date < from_date:
        return False
    return to_date is None or effective_date <= to_date


def ranges_overlap(
    *,
    left_from: date,
    left_to: date | None,
    right_from: date,
    right_to: date | None,
) -> bool:
    """Return whether two inclusive ranges share at least one day.

    Open-ended ranges overlap any range that extends to or beyond their start.
    """
    left_end = left_to if left_to is not None else date.max
    right_end = right_to if right_to is not None else date.max
    return left_from <= right_end and right_from <= left_end


def day_before(value: date) -> date:
    """Return the calendar day immediately before ``value``.

    Used when ending one enrolment the day before another begins, so both ranges
    remain inclusive without sharing a day.
    """
    return value - timedelta(days=1)
