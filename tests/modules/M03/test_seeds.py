"""The baseline seed scenario: deterministic, idempotent, and wholly synthetic.

The seed is what `dev.py seed M03 --scenario baseline` installs and what the
browser suite drives. If it drifts from contracts/M03/fixtures/scenario.json the
reviewed description and the installed rows stop describing each other.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from datetime import UTC, date, datetime

import pytest

from shared import fixtures

pytestmark = pytest.mark.module

CONTRACT = pathlib.Path(__file__).resolve().parents[3] / "contracts" / "M03"


def scenario() -> dict:
    """Load the reviewed description of the baseline the seed installs."""
    return json.loads((CONTRACT / "fixtures" / "scenario.json").read_text())


def test_the_baseline_installs_a_published_revision_with_its_grid(db, clock):
    from modules.timetable.models import PeriodTemplate, Slot, TimetableVersion
    from modules.timetable.seeds import baseline

    baseline(fixtures.SCHOOL_A)

    version = TimetableVersion.objects.get(school_id=fixtures.SCHOOL_A)
    assert version.state == "published"
    assert version.effective_from == date(2026, 6, 1)
    assert PeriodTemplate.objects.count() == 10
    assert Slot.objects.count() == 20


def test_running_the_seed_twice_changes_nothing(db, clock):
    from modules.timetable.models import Slot, TimetableVersion
    from modules.timetable.seeds import baseline

    baseline(fixtures.SCHOOL_A)
    first = TimetableVersion.objects.get(school_id=fixtures.SCHOOL_A).version

    counts = baseline(fixtures.SCHOOL_A)

    assert counts == {
        "timetables": 0,
        "periods": 0,
        "slots": 0,
        "exceptions": 0,
        "substitutions": 0,
    }
    assert Slot.objects.count() == 20
    assert TimetableVersion.objects.get(school_id=fixtures.SCHOOL_A).version == first


def test_the_seeded_ids_are_the_ones_the_reviewed_scenario_names(db, clock):
    """Byte-identical on every machine, which is what the browser suite relies on."""
    from modules.timetable.models import TimetableVersion
    from modules.timetable.seeds import baseline

    baseline(fixtures.SCHOOL_A)

    described = scenario()
    version = TimetableVersion.objects.get(school_id=fixtures.SCHOOL_A)
    assert str(version.id) == described["timetable_v1"]["timetable_id"]
    assert str(version.year_id) == described["structure"]["year"]["year_id"]
    assert version.version == described["timetable_v1"]["version"]


def test_the_seeded_session_identities_match_the_reviewed_scenario(db, clock):
    from modules.timetable.seeds import baseline
    from modules.timetable.sessions import session_id_for

    baseline(fixtures.SCHOOL_A)

    described = scenario()["session_identities"]
    for label, expected in described.items():
        if label == "note":
            continue
        section_label, iso, code = label.split(" ")
        section = fixtures.CLASS_C1 if section_label == "C1" else fixtures.CLASS_C2
        assert (
            str(
                session_id_for(
                    school_id=fixtures.SCHOOL_A,
                    section_id=section,
                    on=date.fromisoformat(iso),
                    slot_code=code,
                )
            )
            == expected
        )


def test_one_seeded_substitution_is_live_and_one_has_expired(db, clock):
    """Both states are seeded so a consumer can be tested against each."""
    from modules.timetable.models import Substitution
    from modules.timetable.seeds import baseline

    baseline(fixtures.SCHOOL_A)

    now = clock.now()
    rows = {row.date: row for row in Substitution.objects.all()}
    assert rows[date(2026, 7, 15)].valid_until > now
    assert rows[date(2026, 7, 8)].valid_until < now
    assert all(row.substitute_teacher_id == fixtures.TEACHER_T2 for row in rows.values())


def test_the_seeded_calendar_marks_a_holiday_and_an_exam_day(db, clock):
    from modules.timetable.models import CalendarException
    from modules.timetable.seeds import baseline
    from modules.timetable.services.reads import ScheduleReader

    baseline(fixtures.SCHOOL_A)

    kinds = {row.date: row.kind for row in CalendarException.objects.all()}
    assert kinds[date(2026, 7, 16)] == "holiday"
    assert kinds[date(2026, 7, 22)] == "exam"

    days = ScheduleReader(clock=clock).calendar_days(
        school_id=fixtures.SCHOOL_A, from_date=date(2026, 7, 15), to_date=date(2026, 7, 22)
    )
    by_date = {day.date: day for day in days}
    assert by_date[date(2026, 7, 16)].is_school_day is False
    assert by_date[date(2026, 7, 22)].is_school_day is True


def test_the_seed_describes_no_real_person_school_or_holiday(db, clock):
    """Synthetic fixtures are expected. Inventing real-looking school data is not."""
    from modules.timetable.seeds import SEED_INSTANT, baseline

    assert SEED_INSTANT == datetime(2026, 7, 15, 4, 30, tzinfo=UTC)
    counts = baseline(fixtures.SCHOOL_A)
    assert counts["timetables"] == 1

    described = scenario()
    assert "synthetic" in described["note"]
    assert described["calendar_exceptions"][0]["reason_key"] == "timetable.reason.holiday"
    # The namespace the ids are derived from is recorded, so anyone can recompute
    # them rather than trusting a committed literal.
    assert described["namespaces"]["m03_seed_rows"]["uuid5_namespace"] == str(
        uuid.uuid5(uuid.NAMESPACE_URL, "https://school.example/contracts/M03/seed")
    )
