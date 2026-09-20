"""Step 4: dated sessions, substitutions, cancellation and teaching authority.

The identity property is the one M04 depends on: a dated period keeps the same
id across a revision, so attendance written against it still reconciles.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from shared import fixtures

from m03_helpers import LAST_WEDNESDAY, SATURDAY_NO_PERIODS, THURSDAY_HOLIDAY, WEDNESDAY, grid

pytestmark = pytest.mark.module

END_OF_SCHOOL_DAY = "2026-07-15T18:30:00+00:00"


def session_for(api, section_id=None, on=WEDNESDAY, slot_code="P1"):
    """Return one session body from the effective schedule."""
    section = section_id or fixtures.CLASS_C1
    body = api.get(f"/timetables/current?section_id={section}&date={on}").json()
    return next(s for s in body["sessions"] if s["slot_code"] == slot_code)


def port(api):
    """Return the in-process timetable service other modules will consume."""
    from modules.timetable.api.deps import timetable_port

    return timetable_port()


# --- stable dated identity -------------------------------------------------


def test_a_session_id_is_derived_from_school_section_date_and_slot_code(api, published):
    """Derived, not stored: the same key must give the same id anywhere."""
    from modules.timetable.sessions import TIMETABLE_SESSION_NAMESPACE, session_id_for

    session = session_for(api, on=WEDNESDAY)

    expected = uuid.uuid5(
        TIMETABLE_SESSION_NAMESPACE,
        f"{fixtures.SCHOOL_A}:{fixtures.CLASS_C1}:{WEDNESDAY}:P1",
    )
    assert session["timetable_session_id"] == str(expected)
    assert session_id_for(
        school_id=fixtures.SCHOOL_A,
        section_id=fixtures.CLASS_C1,
        on=date(2026, 7, 15),
        slot_code="P1",
    ) == expected


def test_a_revision_does_not_create_a_duplicate_attendance_identity(api, published, year_id):
    """Republishing the same weekly grid must reuse every session id."""
    before = session_for(api, on="2026-09-02")["timetable_session_id"]

    later = api.post(
        "/timetables",
        {"year_id": year_id, "effective_from": "2026-09-01", **grid()},
    ).json()
    api.post(f"/timetables/{later['id']}/publish", {"expected_version": later["version"]})

    after = session_for(api, on="2026-09-02")
    assert after["timetable_session_id"] == before
    assert after["timetable_id"] == later["id"]


def test_moving_a_bell_time_in_a_revision_keeps_the_identity(api, published, year_id):
    """Identity keys on the slot code, not the clock time, for exactly this reason."""
    before = session_for(api, on="2026-09-02")["timetable_session_id"]

    moved = grid()
    for period in moved["periods"]:
        if period["slot_code"] == "P1":
            period["starts_at_local"] = "09:00"
            period["ends_at_local"] = "09:25"
    later = api.post(
        "/timetables", {"year_id": year_id, "effective_from": "2026-09-01", **moved}
    ).json()
    api.post(f"/timetables/{later['id']}/publish", {"expected_version": later["version"]})

    after = session_for(api, on="2026-09-02")
    assert after["timetable_session_id"] == before
    assert after["starts_at_local"] == "09:00"


def test_a_session_carries_both_the_revision_id_and_its_version(api, published):
    """Review item 13: the packet's 'timetable_version' was ambiguous, so emit both."""
    session = session_for(api)

    assert session["timetable_id"] == published["id"]
    assert session["timetable_version"] == published["version"]


def test_instants_are_utc_and_local_times_are_school_time(api, published):
    """08:45 Asia/Kolkata on 15 July 2026 is 03:15 UTC."""
    session = session_for(api)

    assert session["starts_at_local"] == "08:45"
    assert session["starts_at"] == "2026-07-15T03:15:00+00:00"
    assert session["ends_at"] == "2026-07-15T04:00:00+00:00"


def test_one_session_is_readable_by_its_identity(api, published):
    session = session_for(api)

    response = api.get(f"/sessions/{session['timetable_session_id']}")

    assert response.status_code == 200
    assert response.json() == session


def test_an_unknown_session_identity_is_404(api, published):
    unknown = uuid.uuid5(fixtures.FIXTURE_NAMESPACE, "not-a-session")

    assert api.get(f"/sessions/{unknown}").status_code == 404


def test_a_weekday_with_no_periods_produces_no_sessions(api, published):
    body = api.get(
        f"/timetables/current?section_id={fixtures.CLASS_C1}&date={SATURDAY_NO_PERIODS}"
    ).json()

    assert body["sessions"] == []
    assert body["is_school_day"] is False


# --- substitutions ---------------------------------------------------------


def test_assigning_a_substitute_defaults_its_expiry_to_the_end_of_that_school_day(
    api, published
):
    """Review item 7. Midnight Asia/Kolkata is 18:30 UTC the previous day."""
    session = session_for(api)

    response = api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["valid_until"] == END_OF_SCHOOL_DAY
    assert body["original_teacher_id"] == str(fixtures.TEACHER_T1)
    assert body["substitute_teacher_id"] == str(fixtures.TEACHER_T2)
    assert body["timetable_session_id"] == session["timetable_session_id"]
    assert body["withdrawn"] is False


def test_a_substitution_appears_on_the_dated_schedule_only(api, published):
    """It is a day override: the recurring grid is untouched."""
    session = session_for(api)
    api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    substituted = session_for(api, on=WEDNESDAY)
    other_day = session_for(api, on="2026-07-17")

    assert substituted["substitute_teacher_id"] == str(fixtures.TEACHER_T2)
    assert other_day["substitute_teacher_id"] is None
    assert api.get(f"/timetables/{published['id']}").json()["version"] == published["version"]


def test_assigning_a_substitute_appends_an_event(api, published):
    from shared.harness.models import HarnessOutboxEvent

    session = session_for(api)
    api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    event = HarnessOutboxEvent.objects.get(event_type="timetable.substitution_assigned")
    assert event.payload["teacher_id"] == str(fixtures.TEACHER_T2)
    assert event.payload["date"] == WEDNESDAY
    assert event.payload["valid_until"] == END_OF_SCHOOL_DAY


def test_a_substitution_may_not_outlive_its_own_school_day(api, published):
    """A substitution is a dated authority, never a standing class permission."""
    session = session_for(api)

    response = api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
            "valid_until": "2026-07-20T18:30:00+00:00",
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.valid_until_after_session_day"


def test_a_substitution_may_not_expire_before_the_period_it_covers(api, published):
    session = session_for(api)

    response = api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
            "valid_until": "2026-07-15T03:30:00+00:00",
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.valid_until_before_session_end"


def test_a_teacher_may_not_substitute_for_themselves(api, published):
    session = session_for(api)

    response = api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T1),
            "reason": "synthetic fixture",
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.substitute_same_as_assigned"


def test_a_substitution_on_a_holiday_is_refused(api, holiday):
    """A holiday has no eligible teaching period to substitute into."""
    session = session_for(api, on=WEDNESDAY)

    response = api.post(
        "/substitutions",
        {
            "date": THURSDAY_HOLIDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    assert response.status_code == 409
    assert response.json()["message_key"] == "timetable.error.date_is_holiday"


def test_a_substitution_on_a_day_the_slot_is_not_taught_is_refused(api, published):
    session = session_for(api)

    response = api.post(
        "/substitutions",
        {
            "date": SATURDAY_NO_PERIODS,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.slot_not_taught_on_date"


def test_a_substitution_outside_the_effective_range_is_refused(api, published):
    session = session_for(api)

    response = api.post(
        "/substitutions",
        {
            "date": "2026-05-27",
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.date_outside_effective_range"


def test_one_period_holds_one_substitute(api, published):
    session = session_for(api)
    body = {
        "date": WEDNESDAY,
        "slot_id": session["slot_id"],
        "teacher_id": str(fixtures.TEACHER_T2),
        "reason": "synthetic fixture",
    }
    assert api.post("/substitutions", body).status_code == 201

    response = api.post("/substitutions", body)

    assert response.status_code == 409
    assert response.json()["message_key"] == "timetable.error.substitution_exists"


def test_a_withdrawn_substitution_frees_the_period_again(api, published):
    session = session_for(api)
    body = {
        "date": WEDNESDAY,
        "slot_id": session["slot_id"],
        "teacher_id": str(fixtures.TEACHER_T2),
        "reason": "synthetic fixture",
    }
    first = api.post("/substitutions", body).json()

    withdrawn = api.put(
        f"/substitutions/{first['id']}",
        {"withdrawn": True, "expected_version": first["version"]},
    )

    assert withdrawn.status_code == 200
    assert session_for(api)["substitute_teacher_id"] is None
    assert api.post("/substitutions", body).status_code == 201


# --- cancellation ----------------------------------------------------------


def test_cancelling_a_session_does_not_touch_the_recurring_schedule(api, published):
    session = session_for(api)

    response = api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {
            "cancelled": True,
            "reason_key": "timetable.reason.cancelled",
            "expected_version": None,
        },
    )

    assert response.status_code == 200, response.content
    assert response.json()["cancelled"] is True
    assert response.json()["cancellation_reason_key"] == "timetable.reason.cancelled"
    assert session_for(api, on="2026-07-17")["cancelled"] is False
    assert api.get(f"/timetables/{published['id']}").json()["version"] == published["version"]


def test_a_cancelled_session_is_shown_rather_than_dropped(api, published):
    session = session_for(api)
    api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": True, "reason_key": None, "expected_version": None},
    )

    body = api.get(
        f"/timetables/current?section_id={fixtures.CLASS_C1}&date={WEDNESDAY}"
    ).json()

    assert len(body["sessions"]) == 2
    assert [s["cancelled"] for s in body["sessions"]] == [True, False]


def test_a_cancellation_can_be_reversed_under_its_own_version(api, published):
    session = session_for(api)
    cancelled = api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": True, "reason_key": None, "expected_version": None},
    ).json()

    restored = api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": False, "reason_key": None, "expected_version": cancelled["version"]},
    )

    assert restored.status_code == 200
    assert session_for(api)["cancelled"] is False


def test_a_stale_cancellation_version_is_refused(api, published):
    session = session_for(api)
    api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": True, "reason_key": None, "expected_version": None},
    )

    response = api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": False, "reason_key": None, "expected_version": None},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"


def test_a_substitute_cannot_be_assigned_to_a_cancelled_session(api, published):
    session = session_for(api)
    api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": True, "reason_key": None, "expected_version": None},
    )

    response = api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    assert response.status_code == 409
    assert response.json()["message_key"] == "timetable.error.session_cancelled"


# --- teaching authority, the fact M04 consumes -----------------------------


def test_teaching_authority_names_the_assigned_teacher(api, published, context_factory):
    context = context_factory(fixtures.TEACHER_T1)
    session = session_for(api)

    authority = port(api).get_teaching_authority(
        context, uuid.UUID(session["timetable_session_id"])
    )

    assert authority.assigned_teacher_id == fixtures.TEACHER_T1
    assert authority.substitute_teacher_id is None
    assert authority.eligible_for_attendance is True


def test_teaching_authority_names_a_live_substitute(api, published, context_factory):
    session = session_for(api)
    api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )

    authority = port(api).get_teaching_authority(
        context_factory(fixtures.TEACHER_T1), uuid.UUID(session["timetable_session_id"])
    )

    assert authority.substitute_teacher_id == fixtures.TEACHER_T2
    assert authority.substitution_valid_until == datetime(2026, 7, 15, 18, 30, tzinfo=UTC)


def test_a_substitution_expires(api, published, context_factory, clock):
    """The packet's 'substitution expires' acceptance case."""
    session = session_for(api)
    api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )
    clock.set(datetime(2026, 7, 16, 4, 30, tzinfo=UTC))

    authority = port(api).get_teaching_authority(
        context_factory(fixtures.TEACHER_T1), uuid.UUID(session["timetable_session_id"])
    )

    assert authority.substitute_teacher_id is None
    assert authority.substitution_valid_until is None


def test_a_cancelled_session_is_not_eligible_for_attendance(api, published, context_factory):
    session = session_for(api)
    api.put(
        f"/sessions/{session['timetable_session_id']}/cancellation",
        {"cancelled": True, "reason_key": None, "expected_version": None},
    )

    authority = port(api).get_teaching_authority(
        context_factory(fixtures.TEACHER_T1), uuid.UUID(session["timetable_session_id"])
    )

    assert authority.cancelled is True
    assert authority.eligible_for_attendance is False


def test_a_holiday_period_is_not_eligible_for_attendance(api, holiday, context_factory):
    """Answering 'no' beats raising: M04 asks a question and gets an answer."""
    from modules.timetable.sessions import session_id_for

    identity = session_id_for(
        school_id=fixtures.SCHOOL_A,
        section_id=fixtures.CLASS_C1,
        on=date(2026, 7, 16),
        slot_code="P1",
    )

    authority = port(api).get_teaching_authority(context_factory(fixtures.TEACHER_T1), identity)

    assert authority.eligible_for_attendance is False
    assert authority.cancelled is False


def test_get_sessions_returns_nothing_on_a_holiday(api, holiday, context_factory):
    sessions = port(api).get_sessions(
        context_factory(fixtures.TEACHER_T1), fixtures.CLASS_C1, date(2026, 7, 16)
    )

    assert sessions == ()


def test_the_port_answers_the_calendar_over_a_range(api, holiday, context_factory):
    days = port(api).get_calendar(
        context_factory(fixtures.TEACHER_T1), date(2026, 7, 15), date(2026, 7, 16)
    )

    assert [day.date for day in days] == [date(2026, 7, 15), date(2026, 7, 16)]
    assert [day.is_school_day for day in days] == [True, False]


def test_a_historical_session_still_resolves_after_a_revision(
    api, published, year_id, context_factory
):
    """Reconciliation depends on it: the old register names the old revision."""
    historical = session_for(api, on=LAST_WEDNESDAY)
    later = api.post(
        "/timetables", {"year_id": year_id, "effective_from": "2026-09-01", **grid()}
    ).json()
    api.post(f"/timetables/{later['id']}/publish", {"expected_version": later["version"]})

    authority = port(api).get_teaching_authority(
        context_factory(fixtures.TEACHER_T1),
        uuid.UUID(historical["timetable_session_id"]),
    )

    assert authority.date == date(2026, 7, 8)
    assert authority.eligible_for_attendance is True
    assert api.get(f"/sessions/{historical['timetable_session_id']}").json()[
        "timetable_id"
    ] == published["id"]
