"""Shared constants and grid builders for M03's suite.

Named ``m03_helpers`` rather than ``helpers`` because pytest's prepend import
mode puts every test helper in one global module namespace, so a generic name
would collide with another module's suite.

Every date here is inside the fixture school term. The weekly pattern is FIXTURE
DATA and not a claim about any school's week: a deployment supplies its own
period templates, which is what makes a date a teaching day.
"""

from __future__ import annotations

from datetime import UTC, datetime

from shared import fixtures

#: The instant every dated assertion in this suite is made from. Inside the
#: fixture term, and a Wednesday, so a Monday-to-Friday grid has periods on it.
FROZEN_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)
WEDNESDAY = "2026-07-15"
THURSDAY_HOLIDAY = "2026-07-16"
FRIDAY = "2026-07-17"
SATURDAY_NO_PERIODS = "2026-07-18"
LAST_WEDNESDAY = "2026-07-08"

#: Weekdays the synthetic grid teaches on. Monday to Friday is FIXTURE DATA, not a
#: claim about any school's week: a deployment supplies its own period templates.
TEACHING_WEEKDAYS = [1, 2, 3, 4, 5]


def grid(*, weekdays=None, slots=None) -> dict:
    """Return a draft body: two periods a day, and the slots taught in them.

    ``slots`` is a list of (weekday, slot_code, section_id, subject_id, teacher_id)
    tuples, or None for the standard baseline grid.
    """
    days = weekdays if weekdays is not None else TEACHING_WEEKDAYS
    periods = [
        {
            "day_of_week": day,
            "slot_code": code,
            "starts_at_local": start,
            "ends_at_local": end,
        }
        for day in days
        for code, start, end in (("P1", "08:45", "09:30"), ("P2", "09:30", "10:15"))
    ]
    if slots is None:
        rows = []
        for day in days:
            rows.append(
                {
                    "day_of_week": day,
                    "slot_code": "P1",
                    "section_id": str(fixtures.CLASS_C1),
                    "subject_id": str(fixtures.SUBJECT_MATHS),
                    "teacher_id": str(fixtures.TEACHER_T1),
                    "room_code": "R1",
                }
            )
            rows.append(
                {
                    "day_of_week": day,
                    "slot_code": "P2",
                    "section_id": str(fixtures.CLASS_C1),
                    "subject_id": str(fixtures.SUBJECT_MALAYALAM),
                    "teacher_id": str(fixtures.TEACHER_T1),
                    "room_code": "R1",
                }
            )
            rows.append(
                {
                    "day_of_week": day,
                    "slot_code": "P1",
                    "section_id": str(fixtures.CLASS_C2),
                    "subject_id": str(fixtures.SUBJECT_MALAYALAM),
                    "teacher_id": str(fixtures.TEACHER_T2),
                    "room_code": None,
                }
            )
    else:
        rows = [
            {
                "day_of_week": day,
                "slot_code": code,
                "section_id": str(section),
                "subject_id": str(subject),
                "teacher_id": str(teacher),
                "room_code": None,
            }
            for day, code, section, subject, teacher in slots
        ]
    return {"periods": periods, "slots": rows}
