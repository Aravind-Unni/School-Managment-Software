"""GET /warnings (the at-risk list) and the attendance figure behind it."""

from __future__ import annotations

import pytest

from modules.performance.services.metrics import attendance_metric_status
from shared import fixtures

pytestmark = [pytest.mark.module]


def test_list_shows_open_warning_with_name_and_class(client, baseline):
    """The teacher sees S1's open warning with the pupil's name and class."""
    res = client.get("/api/v1/warnings")
    assert res.status_code == 200, res.content
    items = res.json()["items"]
    row = next(item for item in items if item["student_id"] == str(fixtures.STUDENT_S1))
    assert row["state"] == "open"
    assert row["rule_code"] == "low_attendance"
    assert row["student_name"]
    assert row["section_label"]


def test_list_leaves_out_pupils_the_caller_cannot_read(client, baseline, as_persona):
    """An unrelated guardian gets an empty list, not S1's warning."""
    as_persona(fixtures.GUARDIAN_G2)
    res = client.get("/api/v1/warnings")
    assert res.status_code == 200, res.content
    assert all(item["student_id"] != str(fixtures.STUDENT_S1) for item in res.json()["items"])


def test_dismissed_warning_leaves_the_active_list(client, baseline):
    """After dismissal the warning shows only under ?state=dismissed."""
    row = client.get("/api/v1/warnings").json()["items"][0]
    client.post(
        f"/api/v1/warnings/{row['id']}/dismiss",
        {"reason": "Medical leave", "expected_version": row["version"]},
        content_type="application/json",
    )
    active = [item["id"] for item in client.get("/api/v1/warnings").json()["items"]]
    assert row["id"] not in active
    dismissed = client.get("/api/v1/warnings", {"state": "dismissed"}).json()["items"]
    assert row["id"] in [item["id"] for item in dismissed]


def test_attendance_computed_from_counts_when_summary_has_no_percentage():
    """8 attended of 10 marked (late counts as attended) is 80.00."""
    value, status = attendance_metric_status(
        percentage=None, eligible=10, unmarked=0, minimum_samples=1, present=7, late=1
    )
    assert (value, status) == ("80.00", "ok")


def test_excused_periods_are_left_out_of_the_total():
    """6 attended of 8 counted (2 excused) is 75.00."""
    value, status = attendance_metric_status(
        percentage=None, eligible=10, unmarked=0, minimum_samples=1, present=6, excused=2
    )
    assert (value, status) == ("75.00", "ok")


def test_a_few_unmarked_periods_do_not_withhold_the_figure():
    """1 unmarked of 10 is within tolerance; 3 of 10 is incomplete."""
    assert attendance_metric_status(
        percentage=None, eligible=10, unmarked=1, minimum_samples=1, present=9
    ) == ("100.00", "ok")
    assert attendance_metric_status(
        percentage=None, eligible=10, unmarked=3, minimum_samples=1, present=7
    ) == (None, "incomplete")


def test_nothing_marked_is_incomplete_not_zero():
    """No marked periods never reads as 0% attendance."""
    assert attendance_metric_status(
        percentage=None, eligible=5, unmarked=5, minimum_samples=1
    ) == (None, "incomplete")
