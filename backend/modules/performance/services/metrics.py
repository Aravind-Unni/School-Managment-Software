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


def attendance_metric_status(
    *,
    percentage: str | None,
    eligible: int,
    unmarked: int,
    minimum_samples: int,
) -> tuple[str | None, str]:
    """Return (value, status) distinguishing incomplete from low attendance.

    Incomplete (unmarked > 0 or eligible below minimum) is never treated as a
    low-percentage trigger input.
    """
    if eligible < minimum_samples:
        return None, "insufficient_data"
    if unmarked > 0 or percentage is None:
        return None, "incomplete"
    return percentage, "ok"
