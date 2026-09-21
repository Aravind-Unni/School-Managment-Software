"""Report-card content: names, marks, percentages and configured grades."""

from __future__ import annotations

from decimal import Decimal

from modules.exchange.services.reportcard_layout import (
    grade_for,
    percent_of,
    report_card_lines,
    subject_lines,
)

CBSE = [
    {"grade": "A1", "min_percent": 91},
    {"grade": "A2", "min_percent": 81},
    {"grade": "B1", "min_percent": 71},
    {"grade": "B2", "min_percent": 61},
    {"grade": "C1", "min_percent": 51},
    {"grade": "C2", "min_percent": 41},
    {"grade": "D", "min_percent": 33},
    {"grade": "E", "min_percent": 0},
]


def test_grade_boundaries_are_inclusive_at_the_minimum():
    assert grade_for(Decimal("91"), CBSE) == "A1"
    assert grade_for(Decimal("90.9"), CBSE) == "A2"
    assert grade_for(Decimal("33"), CBSE) == "D"
    assert grade_for(Decimal("32.9"), CBSE) == "E"


def test_no_bands_means_no_grade_rather_than_a_guess():
    assert grade_for(Decimal("95"), []) is None


def test_zero_maximum_has_no_percentage():
    assert percent_of(Decimal("0"), Decimal("0")) is None


def test_subject_totals_sum_every_published_assessment():
    items = [
        {"subject_id": "m", "score": "18", "max_score": "20"},
        {"subject_id": "m", "score": "70", "max_score": "80"},
        {"subject_id": "e", "score": "40", "max_score": "50"},
        {"subject_id": "e", "score": None, "max_score": "50"},
    ]
    lines = subject_lines(items, {"m": "Mathematics", "e": "English"})
    assert [(row.subject, row.score, row.max_score) for row in lines] == [
        ("English", Decimal("40"), Decimal("50")),
        ("Mathematics", Decimal("88"), Decimal("100")),
    ]


def test_the_card_names_the_pupil_not_their_database_id():
    lines = report_card_lines(
        locale="en",
        school_name="Test School",
        student_name="Anita Nair",
        admission_no="2026-017",
        class_label="Std 5 - A",
        subjects=subject_lines(
            [{"subject_id": "m", "score": "88", "max_score": "100"}], {"m": "Mathematics"}
        ),
        bands=CBSE,
        language_word="English",
        template_version="v1",
    )
    text = "\n".join(lines)
    assert "Test School" in text
    assert "Student: Anita Nair" in text
    assert "Admission no.: 2026-017" in text
    assert "Class: Std 5 - A" in text
    assert "Mathematics | 88 / 100 | 88.0 | A2" in text
    assert "Total | 88 / 100 | 88.0 | A2" in text
