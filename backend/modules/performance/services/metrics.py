"""Pure metric computation from published scores and attendance summaries.

No IO, no clock. Incompatible policy versions are never averaged.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def decimal_string(value: Decimal) -> str:
    """Format a Decimal as a two-place string."""
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def simple_mean_percent(
    scores: list[tuple[str, str, str]],
) -> tuple[str | None, str]:
    """Return (value, status) for simple_mean_v1 over comparable scores.

    Each tuple is (score, max_score, policy_version). Empty → insufficient_data.
    Mixed policy_version → incompatible. Assumes max_score is the same basis
    (denominator 100 in baseline); does not invent CBSE grade letters.
    """
    if not scores:
        return None, "insufficient_data"
    policies = {policy for _, _, policy in scores}
    if len(policies) > 1:
        return None, "incompatible"
    totals: list[Decimal] = []
    for score, max_score, _policy in scores:
        max_d = Decimal(max_score)
        if max_d <= 0:
            return None, "insufficient_data"
        totals.append((Decimal(score) / max_d) * Decimal("100"))
    mean = sum(totals) / Decimal(len(totals))
    return decimal_string(mean), "ok"


#: Share of a pupil's periods that may still be unmarked (a teacher who has
#: not yet submitted, periods later today) before the figure is withheld.
UNMARKED_TOLERANCE = Decimal("0.20")


def attendance_metric_status(
    *,
    percentage: str | None,
    eligible: int,
    unmarked: int,
    minimum_samples: int,
    present: int = 0,
    late: int = 0,
    excused: int = 0,
) -> tuple[str | None, str]:
    """Return (value, status) distinguishing incomplete from low attendance.

    Uses the summary's own percentage when it has one; otherwise attended
    periods (present or late) over marked periods, leaving excused ones out.
    Incomplete (more than UNMARKED_TOLERANCE of periods unmarked, or nothing
    marked) is never treated as a low-percentage trigger input.
    """
    if eligible < minimum_samples:
        return None, "insufficient_data"
    marked = eligible - unmarked
    if marked <= 0 or Decimal(unmarked) > UNMARKED_TOLERANCE * Decimal(eligible):
        return None, "incomplete"
    if percentage is not None:
        return percentage, "ok"
    counted = marked - excused
    if counted <= 0:
        return None, "incomplete"
    attended = Decimal(present + late)
    return decimal_string(attended / Decimal(counted) * Decimal("100")), "ok"
