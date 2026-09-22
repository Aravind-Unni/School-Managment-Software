"""Grade letters from the school's bands."""

from __future__ import annotations

import pytest

from modules.assessment.services.grading import grade_for

pytestmark = [pytest.mark.module]

CBSE = [
    {"grade": "A1", "min_percent": 91},
    {"grade": "A2", "min_percent": 81},
    {"grade": "B1", "min_percent": 71},
    {"grade": "E", "min_percent": 0},
]


def test_first_band_reached_wins():
    assert grade_for("46", "50", CBSE) == "A1"  # 92%
    assert grade_for("40.5", "50", CBSE) == "A2"  # 81% exactly
    assert grade_for("36", "50", CBSE) == "B1"
    assert grade_for("0", "50", CBSE) == "E"


def test_no_grade_without_bands_or_score():
    assert grade_for("40", "50", []) is None
    assert grade_for(None, "50", CBSE) is None
    assert grade_for("40", "0", CBSE) is None
