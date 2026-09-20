"""Step 1: period templates and the draft weekly editor.

Asserts the frozen contract in contracts/M03, not the implementation: every shape
here comes from schemas/dtos.schema.json and openapi.json.
"""

from __future__ import annotations

import pytest
from m03_helpers import grid

from shared import fixtures

pytestmark = pytest.mark.module


def test_creating_a_timetable_always_produces_a_draft(api, year_id):
    """Publication is a separate transition; a create can never skip it."""
    response = api.post(
        "/timetables", {"year_id": year_id, "effective_from": "2026-06-01", **grid()}
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["state"] == "draft"
    assert body["version"] == 1
    assert body["school_id"] == str(fixtures.SCHOOL_A)
    assert body["effective_to"] is None
    assert body["published_at"] is None


def test_the_draft_echoes_its_grid_with_server_assigned_ids(api, draft):
    """A client sends weekday and slot code; the server owns every id."""
    assert len(draft["periods"]) == 10
    assert len(draft["slots"]) == 15
    for period in draft["periods"]:
        assert period["timetable_id"] == draft["id"]
        assert period["school_id"] == str(fixtures.SCHOOL_A)
    codes = {(slot["day_of_week"], slot["slot_code"]) for slot in draft["slots"]}
    assert (3, "P1") in codes and (3, "P2") in codes


def test_the_body_may_not_assert_a_school(api, year_id):
    """Dropping a spoofed field silently hides an attack and a bug equally well."""
    response = api.post(
        "/timetables",
        {
            "year_id": year_id,
            "effective_from": "2026-06-01",
            "school_id": str(fixtures.SCHOOL_B),
            **grid(),
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "error.server_internal_field_rejected"


def test_an_unknown_field_is_refused_rather_than_ignored(api, year_id):
    response = api.post(
        "/timetables",
        {
            "year_id": year_id,
            "effective_from": "2026-06-01",
            "optimise_automatically": True,
            **grid(),
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


def test_an_unknown_field_nested_in_a_slot_is_refused(api, year_id):
    """Closed shapes must stay closed at every depth, which is where one hides."""
    body = {"year_id": year_id, "effective_from": "2026-06-01", **grid()}
    body["slots"][0]["room_id"] = "not-a-declared-field"

    response = api.post("/timetables", body)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("09:30", "09:30", "timetable.error.period_end_not_after_start"),
        ("09:30", "08:45", "timetable.error.period_end_not_after_start"),
    ],
)
def test_a_period_must_end_after_it_starts(api, year_id, start, end, expected):
    body = {"year_id": year_id, "effective_from": "2026-06-01", **grid()}
    body["periods"] = [
        {"day_of_week": 3, "slot_code": "P1", "starts_at_local": start, "ends_at_local": end}
    ]
    body["slots"] = []

    response = api.post("/timetables", body)

    assert response.status_code == 422
    assert response.json()["message_key"] == expected


def test_two_periods_on_one_weekday_may_not_overlap(api, year_id):
    """Half-open comparison: 08:45-09:30 and 09:30-10:15 abut and are fine."""
    body = {"year_id": year_id, "effective_from": "2026-06-01", **grid()}
    body["periods"] = [
        {
            "day_of_week": 3,
            "slot_code": "P1",
            "starts_at_local": "08:45",
            "ends_at_local": "09:30",
        },
        {
            "day_of_week": 3,
            "slot_code": "P2",
            "starts_at_local": "09:15",
            "ends_at_local": "10:00",
        },
    ]
    body["slots"] = []

    response = api.post("/timetables", body)

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.period_overlap"


def test_abutting_periods_are_accepted(api, year_id):
    """The rule is half-open [start, end); an abutting pair is not an overlap."""
    body = {"year_id": year_id, "effective_from": "2026-06-01", **grid(weekdays=[3])}

    assert api.post("/timetables", body).status_code == 201


def test_two_periods_may_not_share_a_weekday_and_slot_code(api, year_id):
    body = {"year_id": year_id, "effective_from": "2026-06-01", **grid()}
    body["periods"] = [
        {
            "day_of_week": 3,
            "slot_code": "P1",
            "starts_at_local": "08:45",
            "ends_at_local": "09:30",
        },
        {
            "day_of_week": 3,
            "slot_code": "P1",
            "starts_at_local": "10:00",
            "ends_at_local": "10:45",
        },
    ]
    body["slots"] = []

    response = api.post("/timetables", body)

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.duplicate_period"


def test_a_slot_naming_a_period_the_grid_does_not_define_is_refused(api, year_id):
    body = {"year_id": year_id, "effective_from": "2026-06-01", **grid(weekdays=[3])}
    body["slots"].append(
        {
            "day_of_week": 3,
            "slot_code": "P9",
            "section_id": str(fixtures.CLASS_C1),
            "subject_id": str(fixtures.SUBJECT_MATHS),
            "teacher_id": str(fixtures.TEACHER_T1),
            "room_code": None,
        }
    )

    response = api.post("/timetables", body)

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.unknown_slot_code"


def test_one_section_may_not_hold_two_slots_in_the_same_period(api, year_id):
    """The packet's unique version/section/period, refused readably at the boundary."""
    body = {
        "year_id": year_id,
        "effective_from": "2026-06-01",
        **grid(
            weekdays=[3],
            slots=[
                (3, "P1", fixtures.CLASS_C1, fixtures.SUBJECT_MATHS, fixtures.TEACHER_T1),
                (3, "P1", fixtures.CLASS_C1, fixtures.SUBJECT_MALAYALAM, fixtures.TEACHER_T2),
            ],
        ),
    }

    response = api.post("/timetables", body)

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.duplicate_slot"


def test_a_slot_naming_a_section_registry_does_not_report_is_refused(api, year_id):
    """M03 confirms a section through get_roster; there is no get_section to ask."""
    unknown = fixtures.fixture_uuid("school_a.section.does_not_exist")
    body = {
        "year_id": year_id,
        "effective_from": "2026-06-01",
        **grid(
            weekdays=[3],
            slots=[(3, "P1", unknown, fixtures.SUBJECT_MATHS, fixtures.TEACHER_T1)],
        ),
    }

    response = api.post("/timetables", body)

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.unknown_section"


def test_effective_to_may_not_precede_effective_from(api, year_id):
    response = api.post(
        "/timetables",
        {
            "year_id": year_id,
            "effective_from": "2026-06-01",
            "effective_to": "2026-05-31",
            **grid(weekdays=[3]),
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.effective_to_before_from"


def test_replacing_a_draft_grid_advances_its_version(api, draft):
    """The editor saves a week, not a cell: one transaction takes it or refuses it."""
    response = api.put(
        f"/timetables/{draft['id']}",
        {
            "effective_from": "2026-06-01",
            "effective_to": None,
            "expected_version": draft["version"],
            **grid(weekdays=[3]),
        },
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["version"] == draft["version"] + 1
    assert len(body["periods"]) == 2
    assert body["state"] == "draft"


def test_replacing_with_a_stale_expected_version_is_refused(api, draft):
    """A second editor holding the old version loses, rather than overwriting."""
    body = {
        "effective_from": "2026-06-01",
        "effective_to": None,
        "expected_version": draft["version"],
        **grid(weekdays=[3]),
    }
    assert api.put(f"/timetables/{draft['id']}", body).status_code == 200

    response = api.put(f"/timetables/{draft['id']}", body)

    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"


def test_the_grid_is_unchanged_after_a_refused_replace(api, draft):
    """A refused write must leave nothing behind."""
    body = {
        "effective_from": "2026-06-01",
        "effective_to": None,
        "expected_version": draft["version"],
        **grid(weekdays=[3]),
    }
    api.put(f"/timetables/{draft['id']}", body)
    after_first = api.get(f"/timetables/{draft['id']}").json()

    api.put(f"/timetables/{draft['id']}", body)

    assert api.get(f"/timetables/{draft['id']}").json() == after_first


def test_a_published_version_cannot_be_edited(api, published):
    """Correcting a published grid is a new revision, so history stays readable."""
    response = api.put(
        f"/timetables/{published['id']}",
        {
            "effective_from": "2026-06-01",
            "effective_to": None,
            "expected_version": published["version"],
            **grid(weekdays=[3]),
        },
    )

    assert response.status_code == 409
    assert response.json()["message_key"] == "timetable.error.not_draft"


def test_listing_returns_items_and_a_next_cursor(api, draft):
    response = api.get("/timetables")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body and "next_cursor" in body
    assert any(item["id"] == draft["id"] for item in body["items"])
    assert "period_count" in body["items"][0]


def test_a_hand_edited_cursor_is_a_422_not_a_500(api, draft):
    response = api.get("/timetables?cursor=not-a-real-cursor")

    assert response.status_code == 422
    assert response.json()["message_key"] == "error.malformed_cursor"


def test_an_unknown_timetable_is_404(api):
    unknown = fixtures.fixture_uuid("school_a.timetable.does_not_exist")

    assert api.get(f"/timetables/{unknown}").status_code == 404
