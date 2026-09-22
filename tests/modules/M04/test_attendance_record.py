"""GET /attendance/students/{id}/record: attendance by subject and month."""

from __future__ import annotations

import pytest

from modules.attendance.seeds import seed_baseline
from shared import fixtures

pytestmark = pytest.mark.module

DATE = fixtures.TERM_SAMPLE_DATE.isoformat()


def test_breakdown_adds_up_to_the_summary(api, clock):
    """Per-subject and per-month rows sum to the same totals as the summary."""
    seed_baseline()
    student = fixtures.STUDENT_S1
    summary = api.get(f"/attendance/summary?student_id={student}&from={DATE}&to={DATE}").json()
    response = api.get(f"/attendance/students/{student}/record?from={DATE}&to={DATE}")
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["total"]["due"] == summary["eligible"]
    assert body["total"]["marked"] == summary["marked"]
    assert sum(row["due"] for row in body["by_subject"]) == summary["eligible"]
    assert sum(row["due"] for row in body["by_month"]) == summary["eligible"]
    assert [row["month"] for row in body["by_month"]] == [DATE[:7]]


def test_percentage_counts_late_as_attended(api, clock):
    """S1 has one present mark out of one marked: 100.00%."""
    seed_baseline()
    body = api.get(
        f"/attendance/students/{fixtures.STUDENT_S1}/record?from={DATE}&to={DATE}"
    ).json()
    assert body["total"]["percentage"] == "100.00"
