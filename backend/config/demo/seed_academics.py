"""Demo academics: a published timetable, attendance history, assessments.

The timetable is a clash-free rotation of the five subject teachers across the
four demo classes. Attendance is taken by each teacher for every period from
the timetable's start up to yesterday, so today is left for you to mark.
Unit Test 1 is marked, approved and published in every class and subject;
Unit Test 2 is created but unmarked, so teachers have marking to do.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta

from .api_actor import ApiActor
from .seed_people import DemoCast

#: The first school day the demo timetable (and attendance history) covers.
TIMETABLE_START = date(2026, 9, 1)

#: Students whose attendance is deliberately poor, so warnings have something to show.
POOR_ATTENDANCE_SHARE = 0.08


def _teachers(cast: DemoCast) -> list[dict]:
    """Return the subject teachers in a fixed order."""
    return [row for row in cast.staff.values() if row["subject"] is not None]


def seed_timetable(principal: ApiActor, cast: DemoCast, school_id) -> None:
    """Fill the installed draft with a rotation and publish it."""
    from modules.timetable.models import PeriodTemplate, TimetableVersion

    draft = TimetableVersion.objects.filter(
        school_id=school_id, year_id=cast.year_id, state="draft"
    ).first()
    template = list(
        PeriodTemplate.objects.filter(timetable=draft).order_by(
            "day_of_week", "starts_at_local"
        )
    )
    days = sorted({row.day_of_week for row in template})
    codes = []
    periods = []
    for row in template:
        periods.append(
            {
                "day_of_week": row.day_of_week,
                "slot_code": row.slot_code,
                "starts_at_local": row.starts_at_local.strftime("%H:%M"),
                "ends_at_local": row.ends_at_local.strftime("%H:%M"),
            }
        )
        if row.day_of_week == days[0]:
            codes.append(row.slot_code)
    teachers = _teachers(cast)
    slots = []
    for day in days:
        for period_index, code in enumerate(codes):
            for section_index, section_id in enumerate(cast.sections.values()):
                teacher = teachers[(section_index + period_index + day) % len(teachers)]
                slots.append(
                    {
                        "day_of_week": day,
                        "slot_code": code,
                        "section_id": section_id,
                        "subject_id": cast.subjects[teacher["subject"]],
                        "teacher_id": teacher["id"],
                        "room_code": None,
                    }
                )
    replaced = principal.put(
        f"/timetables/{draft.id}",
        {
            "effective_from": TIMETABLE_START.isoformat(),
            "effective_to": None,
            "periods": periods,
            "slots": slots,
            "expected_version": draft.version,
        },
    )
    principal.post(
        f"/timetables/{draft.id}/publish",
        {"expected_version": replaced["version"]},
    )


def seed_attendance(cast: DemoCast, actors: dict[str, ApiActor], *, today: date, rng) -> int:
    """Take and submit attendance for every period before today. Returns sessions."""
    poor = {row["id"] for row in cast.students if rng.random() < POOR_ATTENDANCE_SHARE}
    submitted = 0
    day = TIMETABLE_START
    while day < today:
        for login, teacher in cast.staff.items():
            if teacher["subject"] is None:
                continue
            actor = actors[login]
            periods = actor.get("/attendance/periods", {"date": day.isoformat()})["items"]
            for period in periods:
                session = actor.post(
                    "/attendance/sessions",
                    {"timetable_session_id": period["timetable_session_id"]},
                )
                entries = []
                for row in session["roster_snapshot"]:
                    miss = 0.4 if row["student_id"] in poor else 0.04
                    roll = rng.random()
                    status = (
                        "absent" if roll < miss else "late" if roll < miss + 0.02 else "present"
                    )
                    entries.append({"enrolment_id": row["enrolment_id"], "status": status})
                saved = actor.put(
                    f"/attendance/sessions/{session['id']}",
                    {"expected_version": session["version"], "entries": entries},
                )
                actor.post(
                    f"/attendance/sessions/{session['id']}/submit",
                    {"expected_version": saved["version"]},
                    idempotency_key=str(uuid.uuid4()),
                )
                submitted += 1
        day += timedelta(days=1)
    return submitted


def _create_assessment(actor: ApiActor, cast: DemoCast, section_id, subject_id, max_score):
    """Create one written test with a single component; return (body, component id)."""
    component_id = str(uuid.uuid4())
    body = actor.post(
        "/assessments",
        {
            "year_id": cast.year_id,
            "term_id": cast.term_id,
            "section_id": section_id,
            "subject_id": subject_id,
            "type": "written_test",
            "policy_version": "cbse-v1",
            "max_score": f"{max_score}.00",
            "components": [
                {
                    "id": component_id,
                    "max_score": f"{max_score}.00",
                    "weight": "1.000",
                    "topic": None,
                    "question_type": None,
                }
            ],
        },
    )
    return body, component_id


def seed_assessments(
    cast: DemoCast, actors: dict[str, ApiActor], principal: ApiActor, *, rng: random.Random
) -> int:
    """Publish Unit Test 1 everywhere; leave Unit Test 2 unmarked. Returns published."""
    from modules.assessment.models import Result

    ability = {row["id"]: rng.gauss(0.68, 0.15) for row in cast.students}
    published = 0
    for login, teacher in cast.staff.items():
        if teacher["subject"] is None:
            continue
        actor = actors[login]
        subject_id = cast.subjects[teacher["subject"]]
        for section_id in cast.sections.values():
            test, component_id = _create_assessment(actor, cast, section_id, subject_id, 50)
            for result in Result.objects.filter(assessment_id=test["id"]):
                level = min(0.99, max(0.15, ability.get(str(result.student_id), 0.6)))
                absent = rng.random() < 0.03
                score = round(min(50, max(0, rng.gauss(level * 50, 4))) * 2) / 2
                actor.patch(
                    f"/assessments/{test['id']}/results/{result.student_id}",
                    {
                        # Marks are versioned on the assessment, not the result.
                        "expected_version": _assessment_version(test["id"]),
                        "attempt_id": str(result.attempt_id),
                        "status": "draft",
                        "marking_outcome": "absent" if absent else "scored",
                        "component_scores": (
                            []
                            if absent
                            else [{"component_id": component_id, "score": f"{score:.2f}"}]
                        ),
                    },
                )
            version = _assessment_version(test["id"])
            actor.post(f"/assessments/{test['id']}/submit", {"expected_version": version})
            version = _assessment_version(test["id"])
            principal.post(f"/assessments/{test['id']}/approve", {"expected_version": version})
            version = _assessment_version(test["id"])
            principal.post(
                f"/assessments/{test['id']}/publication",
                {"expected_version": version},
                idempotency_key=str(uuid.uuid4()),
            )
            published += 1
            _create_assessment(actor, cast, section_id, subject_id, 50)
    return published


def _assessment_version(assessment_id: str) -> int:
    """Return an assessment's current version (ORM read)."""
    from modules.assessment.models import Assessment

    return Assessment.objects.get(id=assessment_id).version
