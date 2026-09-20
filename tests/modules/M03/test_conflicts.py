"""Step 2: conflict detection.

Two layers. The pure detector is exercised directly with constructed rows,
because several conflicts are unreachable through the API by design -- the write
boundary already refuses them, and the detector re-checks anyway so that a
version written before a rule existed is still caught. The reachable ones are
asserted through the real API.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, date, datetime, time

import pytest
from contracts.people import TeachingAssignment
from shared import fixtures

from m03_helpers import grid

pytestmark = pytest.mark.module

P1 = time(8, 45)
P1_END = time(9, 30)
P2_END = time(10, 15)
JUNE = date(2026, 6, 1)
MARCH = date(2027, 3, 31)


def rows(overlapping_period: bool = False):
    """Return one Wednesday grid as detector inputs: two periods, no slots yet."""
    from modules.timetable.conflicts import PeriodRow

    second_start = time(9, 15) if overlapping_period else P1_END
    return (
        PeriodRow(
            period_id=uuid.uuid5(fixtures.FIXTURE_NAMESPACE, "p1"),
            day_of_week=3,
            slot_code="P1",
            starts_at_local=P1,
            ends_at_local=P1_END,
        ),
        PeriodRow(
            period_id=uuid.uuid5(fixtures.FIXTURE_NAMESPACE, "p2"),
            day_of_week=3,
            slot_code="P2",
            starts_at_local=second_start,
            ends_at_local=P2_END,
        ),
    )


def slot(label, period, *, section, teacher, subject=fixtures.SUBJECT_MATHS):
    """Return one detector slot row."""
    from modules.timetable.conflicts import SlotRow

    return SlotRow(
        slot_id=uuid.uuid5(fixtures.FIXTURE_NAMESPACE, label),
        period_id=period.period_id,
        section_id=section,
        subject_id=subject,
        teacher_id=teacher,
    )


def detect(periods, slots, **overrides):
    """Run the detector with permissive defaults for everything not under test."""
    from modules.timetable.conflicts import detect_conflicts

    arguments = {
        "periods": periods,
        "slots": slots,
        "unavailability": (),
        "assignments": {
            fixtures.TEACHER_T1: (
                TeachingAssignment(
                    section_id=fixtures.CLASS_C1,
                    subject_id=fixtures.SUBJECT_MATHS,
                    from_date=JUNE,
                    to_date=None,
                ),
            )
        },
        "known_sections": frozenset({fixtures.CLASS_C1, fixtures.CLASS_C2}),
        "effective_from": JUNE,
        "effective_to": MARCH,
    }
    arguments.update(overrides)
    return detect_conflicts(**arguments)


def codes(conflicts):
    """Return the set of conflict codes reported."""
    return {conflict.code for conflict in conflicts}


# --- the pure detector -----------------------------------------------------


def test_a_clean_grid_reports_nothing():
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),),
    )

    assert found == ()


def test_one_teacher_in_two_sections_in_the_same_period_is_blocking():
    periods = rows()
    found = detect(
        periods,
        (
            slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
            slot("b", periods[0], section=fixtures.CLASS_C2, teacher=fixtures.TEACHER_T1),
        ),
    )

    assert codes(found) >= {"teacher_double_booked"}
    conflict = next(c for c in found if c.code == "teacher_double_booked")
    assert conflict.blocking is True
    assert conflict.teacher_id == fixtures.TEACHER_T1
    assert len(conflict.slot_ids) == 2


def test_one_teacher_in_two_overlapping_periods_is_blocking():
    """Overlap, not equality: two different periods that share wall-clock time."""
    periods = rows(overlapping_period=True)
    found = detect(
        periods,
        (
            slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
            slot("b", periods[1], section=fixtures.CLASS_C2, teacher=fixtures.TEACHER_T1),
        ),
    )

    assert "teacher_double_booked" in codes(found)


def test_the_same_teacher_in_abutting_periods_is_not_a_conflict():
    """Half-open windows: 08:45-09:30 then 09:30-10:15 is a normal school day."""
    periods = rows()
    found = detect(
        periods,
        (
            slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
            slot("b", periods[1], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
        ),
    )

    assert "teacher_double_booked" not in codes(found)


def test_one_section_in_two_overlapping_periods_is_blocking():
    """Unreachable through the API -- the write refuses overlapping periods first."""
    periods = rows(overlapping_period=True)
    found = detect(
        periods,
        (
            slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
            slot("b", periods[1], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T2),
        ),
    )

    assert "section_double_booked" in codes(found)
    assert all(c.blocking for c in found if c.code == "section_double_booked")


def test_overlapping_period_templates_are_reported_by_the_detector_too():
    """Defence in depth: a version written before the rule existed is still caught."""
    found = detect(rows(overlapping_period=True), ())

    assert "period_overlap" in codes(found)


def test_a_slot_pointing_at_a_missing_period_is_blocking():
    from modules.timetable.conflicts import SlotRow

    periods = rows()
    orphan = SlotRow(
        slot_id=uuid.uuid5(fixtures.FIXTURE_NAMESPACE, "orphan"),
        period_id=uuid.uuid5(fixtures.FIXTURE_NAMESPACE, "gone"),
        section_id=fixtures.CLASS_C1,
        subject_id=fixtures.SUBJECT_MATHS,
        teacher_id=fixtures.TEACHER_T1,
    )

    found = detect(periods, (orphan,))

    assert "slot_references_unknown_period" in codes(found)


def test_a_section_registry_does_not_know_is_blocking():
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),),
        known_sections=frozenset(),
    )

    assert "section_unknown_to_registry" in codes(found)


def test_a_teacher_unavailable_during_a_period_is_blocking_and_names_the_date():
    """The interval is half-open and is expanded only over the effective window."""
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),),
        unavailability=(
            _unavailable(
                fixtures.TEACHER_T1,
                datetime(2026, 7, 15, 3, 0, tzinfo=UTC),
                datetime(2026, 7, 15, 4, 0, tzinfo=UTC),
            ),
        ),
    )

    conflict = next(c for c in found if c.code == "teacher_unavailable")
    assert conflict.blocking is True
    assert conflict.date == date(2026, 7, 15)
    assert conflict.teacher_id == fixtures.TEACHER_T1


def test_unavailability_that_misses_the_period_is_not_a_conflict():
    """08:45-09:30 IST is 03:15-04:00 UTC; an interval ending at 03:00 does not touch it."""
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),),
        unavailability=(
            _unavailable(
                fixtures.TEACHER_T1,
                datetime(2026, 7, 15, 1, 0, tzinfo=UTC),
                datetime(2026, 7, 15, 3, 0, tzinfo=UTC),
            ),
        ),
    )

    assert "teacher_unavailable" not in codes(found)


def test_unavailability_outside_the_effective_window_is_not_a_conflict():
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),),
        effective_to=date(2026, 6, 30),
        unavailability=(
            _unavailable(
                fixtures.TEACHER_T1,
                datetime(2026, 7, 15, 3, 0, tzinfo=UTC),
                datetime(2026, 7, 15, 4, 0, tzinfo=UTC),
            ),
        ),
    )

    assert "teacher_unavailable" not in codes(found)


def test_a_teacher_without_a_registry_assignment_is_reported_but_does_not_block():
    """Review item 4: schools build the grid before the assignment table is complete."""
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C2, teacher=fixtures.TEACHER_T2),),
    )

    conflict = next(c for c in found if c.code == "teacher_not_assigned")
    assert conflict.blocking is False
    assert conflict.teacher_id == fixtures.TEACHER_T2


def test_an_assignment_that_has_lapsed_does_not_count():
    periods = rows()
    found = detect(
        periods,
        (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),),
        assignments={
            fixtures.TEACHER_T1: (
                TeachingAssignment(
                    section_id=fixtures.CLASS_C1,
                    subject_id=fixtures.SUBJECT_MATHS,
                    from_date=date(2025, 6, 1),
                    to_date=date(2025, 12, 31),
                ),
            )
        },
    )

    assert "teacher_not_assigned" in codes(found)


# --- properties ------------------------------------------------------------


def test_detection_does_not_depend_on_the_order_slots_arrive_in():
    """Metamorphic: shuffling the input must not change the answer."""
    periods = rows()
    slots = [
        slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
        slot("b", periods[0], section=fixtures.CLASS_C2, teacher=fixtures.TEACHER_T1),
        slot("c", periods[1], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T2),
    ]
    baseline = codes(detect(periods, tuple(slots)))

    generator = random.Random(20260715)
    for _ in range(12):
        generator.shuffle(slots)
        assert codes(detect(periods, tuple(slots))) == baseline


def test_adding_a_slot_never_removes_a_conflict():
    """Monotonic: a bigger grid cannot resolve a clash the smaller one had."""
    periods = rows()
    clashing = (
        slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),
        slot("b", periods[0], section=fixtures.CLASS_C2, teacher=fixtures.TEACHER_T1),
    )
    before = codes(detect(periods, clashing))

    after = codes(
        detect(
            periods,
            (*clashing, slot("c", periods[1], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1)),
        )
    )

    assert before <= after


def test_the_detector_is_pure():
    """Same inputs, same answer, twice -- no clock and no database reached into."""
    periods = rows()
    slots = (slot("a", periods[0], section=fixtures.CLASS_C1, teacher=fixtures.TEACHER_T1),)

    assert detect(periods, slots) == detect(periods, slots)


# --- through the real API --------------------------------------------------


def test_validate_reports_a_double_booking_and_publish_then_refuses(api, year_id):
    """The packet's headline acceptance case, end to end."""
    body = {
        "year_id": year_id,
        "effective_from": "2026-06-01",
        **grid(
            weekdays=[3],
            slots=[
                (3, "P1", fixtures.CLASS_C1, fixtures.SUBJECT_MATHS, fixtures.TEACHER_T1),
                (3, "P1", fixtures.CLASS_C2, fixtures.SUBJECT_MALAYALAM, fixtures.TEACHER_T1),
            ],
        ),
    }
    created = api.post("/timetables", body)
    assert created.status_code == 201, created.content
    draft = created.json()

    report = api.post(f"/timetables/{draft['id']}/validate")
    assert report.status_code == 200
    reported = report.json()["conflicts"]
    assert any(c["code"] == "teacher_double_booked" and c["blocking"] for c in reported)
    assert len(next(c for c in reported if c["code"] == "teacher_double_booked")["slot_ids"]) == 2

    refused = api.post(
        f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]}
    )
    assert refused.status_code == 409
    assert refused.json()["message_key"] == "timetable.error.conflicts_present"
    assert api.get(f"/timetables/{draft['id']}").json()["state"] == "draft"


def test_validate_is_read_only(api, draft):
    """An empty conflict list is an observation, not a reservation."""
    before = api.get(f"/timetables/{draft['id']}").json()

    api.post(f"/timetables/{draft['id']}/validate")

    assert api.get(f"/timetables/{draft['id']}").json() == before


def test_a_recorded_unavailability_blocks_publication(api, draft):
    """T1 teaches every weekday in the baseline grid, so any weekday clash blocks."""
    recorded = api.post(
        "/teacher-unavailability",
        {
            "staff_id": str(fixtures.TEACHER_T1),
            "starts_at": "2026-07-15T03:00:00+00:00",
            "ends_at": "2026-07-15T04:00:00+00:00",
            "reason_key": "timetable.reason.unavailable",
        },
    )
    assert recorded.status_code == 201, recorded.content

    report = api.post(f"/timetables/{draft['id']}/validate").json()

    assert any(c["code"] == "teacher_unavailable" for c in report["conflicts"])
    refused = api.post(
        f"/timetables/{draft['id']}/publish", {"expected_version": draft["version"]}
    )
    assert refused.status_code == 409


def test_a_withdrawn_unavailability_stops_blocking(api, draft):
    recorded = api.post(
        "/teacher-unavailability",
        {
            "staff_id": str(fixtures.TEACHER_T1),
            "starts_at": "2026-07-15T03:00:00+00:00",
            "ends_at": "2026-07-15T04:00:00+00:00",
            "reason_key": None,
        },
    ).json()

    withdrawn = api.put(
        f"/teacher-unavailability/{recorded['id']}",
        {
            "starts_at": recorded["starts_at"],
            "ends_at": recorded["ends_at"],
            "reason_key": None,
            "withdrawn": True,
            "expected_version": recorded["version"],
        },
    )

    assert withdrawn.status_code == 200
    report = api.post(f"/timetables/{draft['id']}/validate").json()
    assert not any(c["code"] == "teacher_unavailable" for c in report["conflicts"])


def test_an_unavailability_must_end_after_it_starts():
    response = api.post(
        "/teacher-unavailability",
        {
            "staff_id": str(fixtures.TEACHER_T1),
            "starts_at": "2026-07-15T04:00:00+00:00",
            "ends_at": "2026-07-15T04:00:00+00:00",
            "reason_key": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["message_key"] == "timetable.error.unavailability_end_not_after_start"


def _unavailable(staff_id, starts_at, ends_at):
    """Return one detector unavailability row."""
    from modules.timetable.conflicts import UnavailabilityRow

    return UnavailabilityRow(staff_id=staff_id, starts_at=starts_at, ends_at=ends_at)
