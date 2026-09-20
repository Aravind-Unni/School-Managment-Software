"""Step 3: publication, effective-version selection and the school calendar.

The properties that matter here are historical: a published grid must stay
readable forever, because a register taken last term was taken against it.
"""

from __future__ import annotations

import pytest
from m03_helpers import (
    FRIDAY,
    SATURDAY_NO_PERIODS,
    THURSDAY_HOLIDAY,
    WEDNESDAY,
    grid,
)

from shared import fixtures

pytestmark = pytest.mark.module

SEPTEMBER = "2026-09-01"
LAST_DAY_OF_V1 = "2026-08-31"


def second_version(api, year_id, effective_from=SEPTEMBER):
    """Create and return a second draft, effective later than the baseline."""
    response = api.post(
        "/timetables",
        {
            "year_id": year_id,
            "effective_from": effective_from,
            **grid(
                slots=[
                    (
                        day,
                        "P1",
                        fixtures.CLASS_C1,
                        fixtures.SUBJECT_MALAYALAM,
                        fixtures.TEACHER_T1,
                    )
                    for day in (1, 2, 3, 4, 5)
                ]
            ),
        },
    )
    assert response.status_code == 201, response.content
    return response.json()


# --- publishing ------------------------------------------------------------


def test_publishing_a_clean_draft_makes_it_effective(api, draft):
    response = api.post(
        f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]}
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["state"] == "published"
    assert body["effective_from"] == "2026-06-01"
    assert body["superseded_timetable_id"] is None
    assert body["version"] == draft["version"] + 1

    reread = api.get(f"/timetables/{draft['id']}").json()
    assert reread["state"] == "published"
    assert reread["published_at"] is not None


def test_publishing_appends_an_event_and_an_audit_row(api, draft):
    """Both must land in the writing transaction, not afterwards."""
    from shared.harness.models import HarnessAuditRecord, HarnessOutboxEvent

    api.post(f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]})

    event = HarnessOutboxEvent.objects.get(event_type="timetable.published")
    assert event.school_id == fixtures.SCHOOL_A
    assert event.aggregate_id == __import__("uuid").UUID(draft["id"])
    assert event.payload["effective_from"] == "2026-06-01"
    assert event.aggregate_version == draft["version"] + 1
    assert HarnessAuditRecord.objects.filter(action="timetable.publish").count() == 1


def test_publication_notifies_through_the_outbox_and_not_a_direct_send(api, draft):
    """An SMS outage must never be able to stop a timetable being published."""
    from modules.timetable.registration import REGISTRATION

    assert "notifications" not in REGISTRATION.consumers

    assert (
        api.post(
            f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]}
        ).status_code
        == 200
    )


def test_a_failed_publish_leaves_no_audit_row_no_event_and_no_state_change(api, draft):
    """The rollback assertion: the Platform adapter joins the caller's transaction."""
    from shared.fakes.failures import InjectedFailure
    from shared.harness.models import HarnessAuditRecord, HarnessOutboxEvent
    from shared.ports import runtime

    platform = runtime.get_registry().resolve("platform")
    # The port registry is process-global, so the injector's call counters carry
    # across tests. Plan the failure for the NEXT call rather than the first one
    # ever, or an earlier test in the same process consumes it.
    platform._failures.fail(
        "platform.append_event",
        on_call=platform._failures.call_count("platform.append_event") + 1,
    )

    with pytest.raises(InjectedFailure):
        api.post(f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]})

    # The draft's own creation audit row is expected and is not what rolled back.
    assert HarnessOutboxEvent.objects.count() == 0
    assert HarnessAuditRecord.objects.filter(action="timetable.publish").count() == 0
    assert api.get(f"/timetables/{draft['id']}").json()["state"] == "draft"


def test_two_concurrent_publishes_of_one_draft_produce_exactly_one_published_version(
    api, draft
):
    """Both callers read version 1. One wins; the other is told, not overwritten."""
    from shared.harness.models import HarnessOutboxEvent

    body = {"expected_version": draft["version"]}
    first = api.post(f"/timetables/{draft['id']}/publish", body)
    second = api.post(f"/timetables/{draft['id']}/publish", body)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == "version_conflict"
    assert HarnessOutboxEvent.objects.filter(event_type="timetable.published").count() == 1


def test_republishing_an_already_published_version_is_a_state_conflict(api, published):
    """Distinct from a version conflict: the version is current, the state is wrong."""
    response = api.post(
        f"/timetables/{published['id']}/publish", {"expected_version": published["version"]}
    )

    assert response.status_code == 409
    assert response.json()["message_key"] == "timetable.error.already_published"


def test_publishing_closes_the_previous_version_rather_than_deleting_it(
    api, published, year_id
):
    later = second_version(api, year_id)

    result = api.post(
        f"/timetables/{later['id']}/publish", {"expected_version": later["version"]}
    ).json()

    assert result["superseded_timetable_id"] == published["id"]
    previous = api.get(f"/timetables/{published['id']}").json()
    assert previous["state"] == "superseded"
    assert previous["effective_to"] == LAST_DAY_OF_V1
    assert len(previous["slots"]) == 15


def test_a_superseded_version_is_still_listed(api, published, year_id):
    """Historical versions must stay available for reconciliation."""
    later = second_version(api, year_id)
    api.post(f"/timetables/{later['id']}/publish", {"expected_version": later["version"]})

    listed = api.get("/timetables?state=superseded").json()["items"]

    assert [item["id"] for item in listed] == [published["id"]]


def test_the_effective_version_is_chosen_by_date(api, published, year_id):
    """The current/historical selection the packet names as an acceptance case."""
    later = second_version(api, year_id)
    api.post(f"/timetables/{later['id']}/publish", {"expected_version": later["version"]})

    historical = api.get(
        f"/timetables/current?section_id={fixtures.CLASS_C1}&date={LAST_DAY_OF_V1}"
    ).json()
    current = api.get(
        f"/timetables/current?section_id={fixtures.CLASS_C1}&date=2026-09-02"
    ).json()

    assert historical["timetable_id"] == published["id"]
    assert current["timetable_id"] == later["id"]
    assert {s["subject_id"] for s in current["sessions"]} == {str(fixtures.SUBJECT_MALAYALAM)}


def test_publication_is_forward_only(api, published, year_id):
    """Rewriting the grid a past register was taken against is refused."""
    retrospective = second_version(api, year_id, effective_from="2026-05-01")

    response = api.post(
        f"/timetables/{retrospective['id']}/publish",
        {"expected_version": retrospective["version"]},
    )

    assert response.status_code == 409
    assert (
        response.json()["message_key"] == "timetable.error.effective_from_not_after_effective"
    )


def test_reading_a_date_no_published_version_covers_is_a_state_conflict(api, draft):
    """A draft is never served to a schedule reader."""
    response = api.get(f"/timetables/current?section_id={fixtures.CLASS_C1}&date={WEDNESDAY}")

    assert response.status_code == 409
    assert response.json()["message_key"] == "timetable.error.no_effective_timetable"


# --- the calendar ----------------------------------------------------------


def test_a_weekday_the_grid_teaches_is_a_school_day(api, published):
    days = api.get(f"/calendar?from_date={WEDNESDAY}&to_date={FRIDAY}").json()["days"]

    assert [day["date"] for day in days] == [WEDNESDAY, THURSDAY_HOLIDAY, FRIDAY]
    assert days[0]["is_school_day"] is True
    assert days[0]["reason_key"] is None
    assert days[0]["kinds"] == []


def test_a_weekday_with_no_periods_is_not_a_school_day(api, published):
    """Derived from the school's own period templates, never from a built-in week."""
    days = api.get(
        f"/calendar?from_date={SATURDAY_NO_PERIODS}&to_date={SATURDAY_NO_PERIODS}"
    ).json()["days"]

    assert days[0]["is_school_day"] is False
    assert days[0]["reason_key"] == "timetable.reason.no_periods"
    assert days[0]["kinds"] == []


def test_a_holiday_is_not_a_school_day(api, holiday):
    days = api.get(f"/calendar?from_date={THURSDAY_HOLIDAY}&to_date={THURSDAY_HOLIDAY}").json()[
        "days"
    ]

    assert days[0]["is_school_day"] is False
    assert days[0]["reason_key"] == "timetable.reason.holiday"
    assert days[0]["kinds"] == ["holiday"]


def test_a_holiday_has_no_eligible_teaching_period(api, holiday):
    """The packet's 'holiday excluded' acceptance case."""
    body = api.get(
        f"/timetables/current?section_id={fixtures.CLASS_C1}&date={THURSDAY_HOLIDAY}"
    ).json()

    assert body["is_school_day"] is False
    assert body["reason_key"] == "timetable.reason.holiday"
    assert body["sessions"] == []


def test_an_exam_day_is_still_a_teaching_day(api, published):
    """Exams are shown, but they do not remove the day's periods."""
    created = api.post(
        "/calendar-exceptions",
        {"date": "2026-07-22", "kind": "exam", "reason_key": "timetable.reason.exam"},
    )
    assert created.status_code == 201, created.content

    days = api.get("/calendar?from_date=2026-07-22&to_date=2026-07-22").json()["days"]
    sessions = api.get(
        f"/timetables/current?section_id={fixtures.CLASS_C1}&date=2026-07-22"
    ).json()

    assert days[0]["is_school_day"] is True
    assert days[0]["kinds"] == ["exam"]
    assert len(sessions["sessions"]) == 2


def test_withdrawing_a_holiday_restores_the_teaching_day(api, holiday):
    response = api.put(
        f"/calendar-exceptions/{holiday['id']}",
        {
            "kind": "holiday",
            "reason_key": holiday["reason_key"],
            "withdrawn": True,
            "expected_version": holiday["version"],
        },
    )

    assert response.status_code == 200
    assert response.json()["withdrawn"] is True
    days = api.get(f"/calendar?from_date={THURSDAY_HOLIDAY}&to_date={THURSDAY_HOLIDAY}").json()[
        "days"
    ]
    assert days[0]["is_school_day"] is True


def test_withdrawing_with_a_stale_version_is_refused(api, holiday):
    body = {
        "kind": "holiday",
        "reason_key": None,
        "withdrawn": True,
        "expected_version": holiday["version"],
    }
    assert api.put(f"/calendar-exceptions/{holiday['id']}", body).status_code == 200

    response = api.put(f"/calendar-exceptions/{holiday['id']}", body)

    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"


def test_recording_the_same_exception_twice_is_refused(api, holiday):
    """One date holds one exception of a kind; a second is a mistake, not a second holiday."""
    response = api.post(
        "/calendar-exceptions",
        {"date": THURSDAY_HOLIDAY, "kind": "holiday", "reason_key": None},
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["field_errors"]] == ["date"]


def test_recording_an_exception_that_was_withdrawn_reinstates_it(api, holiday):
    """Withdraw is not delete, so the same date and kind must be reusable."""
    api.put(
        f"/calendar-exceptions/{holiday['id']}",
        {
            "kind": "holiday",
            "reason_key": None,
            "withdrawn": True,
            "expected_version": holiday["version"],
        },
    )

    response = api.post(
        "/calendar-exceptions",
        {"date": THURSDAY_HOLIDAY, "kind": "holiday", "reason_key": "timetable.reason.holiday"},
    )

    assert response.status_code == 201
    assert response.json()["id"] == holiday["id"]
    assert response.json()["withdrawn"] is False


def test_a_calendar_range_must_not_run_backwards(api, published):
    response = api.get(f"/calendar?from_date={FRIDAY}&to_date={WEDNESDAY}")

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.to_date_before_from_date"


def test_a_calendar_range_is_bounded(api, published):
    """One request must not be able to expand an unbounded date walk."""
    response = api.get("/calendar?from_date=2026-01-01&to_date=2028-01-01")

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.range_too_wide"
