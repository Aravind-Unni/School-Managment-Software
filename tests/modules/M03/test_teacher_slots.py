"""GET /teacher-slots: the periods a teacher actually has, for scheduling.

The Assessments screen sets a class test into a lesson the teacher already has
with that class, so this endpoint answers "when am I with C1 for maths?" rather
than letting the teacher type any time at all.

Written against the endpoint's contract: earliest first, cancelled periods and
closed days left out, filters on section and subject, range capped.
"""

from __future__ import annotations

import pytest
from m03_helpers import THURSDAY_HOLIDAY, WEDNESDAY

from shared import fixtures

pytestmark = pytest.mark.module

MONDAY = "2026-07-13"
NEXT_WEDNESDAY = "2026-07-22"


def slots(api, **query):
    """Return the items of one /teacher-slots call, failing loudly on error."""
    parts = "&".join(f"{key}={value}" for key, value in query.items())
    response = api.get(f"/teacher-slots?{parts}")
    assert response.status_code == 200, response.content
    return response.json()["items"]


def test_a_teacher_gets_their_own_periods_earliest_first(api, published):
    """The week's lessons come back in the order they will be taught."""
    items = slots(
        api,
        staff_id=fixtures.TEACHER_T1,
        **{"from": MONDAY, "to": NEXT_WEDNESDAY},
    )

    assert items, "T1 teaches every weekday in the baseline grid"
    keys = [(row["date"], row["starts_at_local"]) for row in items]
    assert keys == sorted(keys)
    assert {row["slot_code"] for row in items} == {"P1", "P2"}


def test_filters_narrow_the_list_to_one_class_and_subject(api, published):
    """Choosing C1 maths must not offer the malayalam period in the same day."""
    items = slots(
        api,
        staff_id=fixtures.TEACHER_T1,
        section_id=fixtures.CLASS_C1,
        subject_id=fixtures.SUBJECT_MATHS,
        **{"from": MONDAY, "to": NEXT_WEDNESDAY},
    )

    assert items
    assert {row["slot_code"] for row in items} == {"P1"}
    assert all(row["section_id"] == str(fixtures.CLASS_C1) for row in items)
    assert all(row["subject_id"] == str(fixtures.SUBJECT_MATHS) for row in items)


def test_a_closed_day_offers_nothing(api, published, holiday):
    """A holiday has no lessons, so no test can be set on it."""
    items = slots(
        api,
        staff_id=fixtures.TEACHER_T1,
        **{"from": THURSDAY_HOLIDAY, "to": THURSDAY_HOLIDAY},
    )

    assert items == []


def test_a_cancelled_period_is_not_offered(api, published):
    """Cancel P1 on the Wednesday and it disappears from that day's choices."""
    session = next(
        row
        for row in api.get(
            f"/timetables/current?section_id={fixtures.CLASS_C1}&date={WEDNESDAY}"
        ).json()["sessions"]
        if row["slot_code"] == "P1"
    )
    cancelled = api.put(
        f"/timetable-sessions/{session['timetable_session_id']}/cancellation",
        {
            "cancelled": True,
            "reason_key": "timetable.reason.cancelled",
            "expected_version": None,
        },
    )
    assert cancelled.status_code == 200, cancelled.content

    items = slots(
        api,
        staff_id=fixtures.TEACHER_T1,
        section_id=fixtures.CLASS_C1,
        subject_id=fixtures.SUBJECT_MATHS,
        **{"from": WEDNESDAY, "to": WEDNESDAY},
    )

    assert items == []


@pytest.mark.parametrize(
    "query",
    [
        {"from": "2026-07-13", "to": "2026-07-12"},
        {"from": "2026-01-01", "to": "2026-12-31"},
    ],
)
def test_a_backwards_or_enormous_range_is_refused(api, published, query):
    """Walking a year of days per keystroke is a mistake, not a request."""
    parts = "&".join(f"{key}={value}" for key, value in query.items())
    response = api.get(f"/teacher-slots?staff_id={fixtures.TEACHER_T1}&{parts}")

    assert response.status_code == 422, response.content


def test_the_staff_member_and_the_range_are_required(api, published):
    """Without them there is no question to answer."""
    assert api.get("/teacher-slots").status_code == 422
    assert api.get(f"/teacher-slots?staff_id={fixtures.TEACHER_T1}").status_code == 422
