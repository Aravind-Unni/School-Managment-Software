"""Money, marks and time primitives with one representation each.

Two rules the whole product depends on:
  * Money is an integer count of INR paise. There is no float rupee anywhere.
  * Marks cross the wire as a decimal *string* so that 8.5 never becomes
    8.499999999999999 in JavaScript.

Does not handle: currency other than INR, or rounding policy for fee
proration (M07 owns that and must declare it in its own contract).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

#: School-local civil timezone. Calendar dates (attendance day, fee due date,
#: exam date) are computed in this zone; instants are always stored in UTC.
SCHOOL_TIMEZONE = ZoneInfo("Asia/Kolkata")

#: Marks are stored with at most this many decimal places.
MARKS_DECIMAL_PLACES = 2


def now_utc() -> datetime:
    """Return the current instant as timezone-aware UTC.

    Does not handle: test freezing. Tests inject a ClockPort instead of
    monkeypatching this, so that frozen time is explicit at the call site.
    """
    return datetime.now(UTC)


def school_date(instant: datetime) -> date:
    """Convert a UTC instant to the civil date at the school.

    Assumes ``instant`` is timezone-aware. A 19:00 UTC mark on 30 June is
    1 July at the school, and attendance must agree with the school, not UTC.
    """
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    return instant.astimezone(SCHOOL_TIMEZONE).date()


def paise_from_rupee_string(text: str) -> int:
    """Parse a human rupee string such as "1250.50" into 125050 paise.

    Raises ValueError on more than two decimal places rather than rounding,
    because silently dropping a paisa in a fee ledger is unrecoverable.

    Does not handle: thousands separators or currency symbols.
    """
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a decimal amount: {text!r}") from exc
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"more precision than paise: {text!r}")
    return int(amount.scaleb(2).to_integral_exact())


def rupee_string_from_paise(paise: int) -> str:
    """Render paise as a two-decimal rupee string for display and exports."""
    return f"{Decimal(paise) / 100:.2f}"


def validate_marks_string(text: str) -> str:
    """Return ``text`` unchanged if it is a valid marks decimal string.

    Valid means: parseable as Decimal, not negative, finite, and no more than
    MARKS_DECIMAL_PLACES decimal places.

    Does not handle: the per-assessment maximum. Only M05 knows that a paper is
    out of 80, so range checking lives there.
    """
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a decimal mark: {text!r}") from exc
    if not value.is_finite():
        raise ValueError(f"mark must be finite: {text!r}")
    if value < 0:
        raise ValueError(f"mark must not be negative: {text!r}")
    if value.as_tuple().exponent < -MARKS_DECIMAL_PLACES:
        raise ValueError(f"mark has more than {MARKS_DECIMAL_PLACES} places: {text!r}")
    return text
