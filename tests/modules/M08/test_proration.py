"""Part-month bus fees."""

from __future__ import annotations

from datetime import date

import pytest

from modules.transport.services.period import prorated_amount

pytestmark = [pytest.mark.module]


def test_daily_charges_days_used_rounded_to_rupees():
    # Joined 16 Sept: 15 of 30 days of a ₹1,200 month.
    assert (
        prorated_amount(
            amount_paise=120000,
            from_date=date(2026, 9, 16),
            to_date=None,
            period="2026-09",
            policy="daily",
        )
        == 60000
    )


def test_full_rule_charges_the_whole_month():
    assert (
        prorated_amount(
            amount_paise=120000,
            from_date=date(2026, 9, 16),
            to_date=None,
            period="2026-09",
            policy="full",
        )
        == 120000
    )


def test_left_before_the_month_is_nothing():
    assert (
        prorated_amount(
            amount_paise=120000,
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 31),
            period="2026-09",
            policy="daily",
        )
        == 0
    )
