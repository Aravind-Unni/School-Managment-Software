"""Who may see which schedule, and what a cross-school probe learns: nothing.

Every denial here is produced by the deny-by-default fake Access plus the
relationship the module resolved from Registry. There is no test-only bypass, so
the authorisation path these tests exercise is the one that ships.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from contracts.errors import StaleAuth
from contracts.identity import AuthLevel
from shared import fixtures

from m03_helpers import WEDNESDAY

pytestmark = pytest.mark.module

C1 = fixtures.CLASS_C1
C2 = fixtures.CLASS_C2


@pytest.fixture
def recorded_access(monkeypatch):
    """Record every (action, facts) pair the module asks Access about.

    The packet asks fakes to record calls for assertions. FakeAccess does not, and
    it is shared, so the recording is wrapped here rather than added to it.
    """
    from shared.ports import runtime

    adapter = runtime.get_registry().resolve("access")
    calls: list[tuple[str, object]] = []
    original = adapter.authorize

    def recording(context, action, facts):
        calls.append((action, facts))
        return original(context, action, facts)

    monkeypatch.setattr(adapter, "authorize", recording)
    return calls


# --- section reads ---------------------------------------------------------


def test_an_assigned_teacher_may_read_their_section(api, published):
    response = api.get(f"/timetables/current?section_id={C1}&date={WEDNESDAY}")

    assert response.status_code == 200
    assert len(response.json()["sessions"]) == 2


def test_a_teacher_with_no_assignment_to_the_section_is_denied(api, published, as_persona):
    """The packet's 'unrelated class denied' acceptance case. T2 teaches nothing."""
    as_persona(fixtures.TEACHER_T2)

    response = api.get(f"/timetables/current?section_id={C1}&date={WEDNESDAY}")

    assert response.status_code == 403
    assert response.json()["code"] == "action_denied"


def test_a_guardian_reads_their_own_child_s_section(api, published, as_persona):
    as_persona(fixtures.GUARDIAN_G1)

    response = api.get(
        f"/timetables/current?section_id={C1}&date={WEDNESDAY}&student_id={fixtures.STUDENT_S1}"
    )

    assert response.status_code == 200


def test_a_guardian_of_another_section_s_child_is_denied(api, published, as_persona):
    """G2 guards S3, who is in C2. C1 is not theirs to read."""
    as_persona(fixtures.GUARDIAN_G2)

    response = api.get(
        f"/timetables/current?section_id={C1}&date={WEDNESDAY}&student_id={fixtures.STUDENT_S3}"
    )

    assert response.status_code == 403


def test_a_guardian_may_not_name_a_child_they_do_not_guard(api, published, as_persona):
    """Naming S1 does not make G2 related to S1; Registry is asked, not the client."""
    as_persona(fixtures.GUARDIAN_G2)

    response = api.get(
        f"/timetables/current?section_id={C1}&date={WEDNESDAY}&student_id={fixtures.STUDENT_S1}"
    )

    assert response.status_code == 403


def test_a_guardian_without_naming_a_child_is_denied(api, published, as_persona):
    as_persona(fixtures.GUARDIAN_G1)

    response = api.get(f"/timetables/current?section_id={C1}&date={WEDNESDAY}")

    assert response.status_code == 403


def test_a_pupil_may_read_their_own_section(api, published, as_persona):
    as_persona(fixtures.STUDENT_S1)

    response = api.get(
        f"/timetables/current?section_id={C1}&date={WEDNESDAY}&student_id={fixtures.STUDENT_S1}"
    )

    assert response.status_code == 200


def test_a_section_read_asks_access_with_the_relationship_registry_reported(
    api, published, recorded_access
):
    """The module folds Registry's answer into ScopeFacts; it decides nothing itself."""
    api.get(f"/timetables/current?section_id={C1}&date={WEDNESDAY}")

    action, facts = next(
        call for call in recorded_access if call[0] == "timetable.read_section"
    )
    assert facts.section_id == C1
    assert facts.resource_school_id == fixtures.SCHOOL_A
    assert facts.relationship is not None


# --- pupil and teacher day views -------------------------------------------


def test_a_pupil_day_marks_the_subjects_they_are_not_enrolled_in(api, published, as_persona):
    """S2 takes malayalam only; the maths period is a free period for them."""
    as_persona(fixtures.GUARDIAN_G1)

    body = api.get(f"/student-schedule?student_id={fixtures.STUDENT_S2}&date={WEDNESDAY}").json()

    by_subject = {row["session"]["subject_id"]: row["enrolled"] for row in body["sessions"]}
    assert by_subject[str(fixtures.SUBJECT_MATHS)] is False
    assert by_subject[str(fixtures.SUBJECT_MALAYALAM)] is True
    assert body["section_id"] == str(C1)


def test_an_unrelated_actor_may_not_read_a_pupil_s_day(api, published, as_persona):
    as_persona(fixtures.GUARDIAN_G2)

    response = api.get(f"/student-schedule?student_id={fixtures.STUDENT_S1}&date={WEDNESDAY}")

    assert response.status_code == 403


def test_a_teacher_reads_their_own_day(api, published):
    body = api.get(f"/teacher-schedule?staff_id={fixtures.TEACHER_T1}&date={WEDNESDAY}").json()

    assert body["staff_id"] == str(fixtures.TEACHER_T1)
    assert {s["slot_code"] for s in body["sessions"]} == {"P1", "P2"}
    assert body["is_school_day"] is True


def test_a_teacher_s_day_includes_the_periods_they_are_substituting(api, published, as_persona):
    session = api.get(f"/timetables/current?section_id={C1}&date={WEDNESDAY}").json()[
        "sessions"
    ][0]
    api.post(
        "/substitutions",
        {
            "date": WEDNESDAY,
            "slot_id": session["slot_id"],
            "teacher_id": str(fixtures.TEACHER_T2),
            "reason": "synthetic fixture",
        },
    )
    as_persona(fixtures.TEACHER_T2)

    body = api.get(f"/teacher-schedule?staff_id={fixtures.TEACHER_T2}&date={WEDNESDAY}").json()

    assert session["timetable_session_id"] in {
        s["timetable_session_id"] for s in body["sessions"]
    }


def test_reading_another_staff_member_s_day_is_authorised_as_an_edit(
    api, published, recorded_access
):
    """A teacher reads their own day; seeing someone else's is timetable.edit work.

    The fake grants every school-scoped action to every persona, so the DENIAL
    cannot be shown here -- what can be shown, and is what matters, is WHICH
    action the module asks about. Recorded as a pending case in the handoff.
    """
    api.get(f"/teacher-schedule?staff_id={fixtures.TEACHER_T2}&date={WEDNESDAY}")

    actions = [action for action, _ in recorded_access]
    assert "timetable.edit" in actions
    assert "timetable.read_teacher" not in actions


# --- two-school isolation --------------------------------------------------


def test_another_school_s_timetable_is_404_not_403(api, published):
    """Existence must not be disclosed, so absent and not-yours look identical."""
    from modules.timetable.models import TimetableVersion

    theirs = TimetableVersion.objects.create(
        school_id=fixtures.SCHOOL_B,
        year_id=uuid.uuid4(),
        effective_from="2026-06-01",
        state="published",
        version=1,
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
        updated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert api.get(f"/timetables/{theirs.id}").status_code == 404
    assert api.get("/timetables").json()["items"] != []
    assert all(
        item["id"] != str(theirs.id) for item in api.get("/timetables").json()["items"]
    )


def test_another_school_s_session_identity_is_404(api, published):
    from modules.timetable.sessions import session_id_for

    theirs = session_id_for(
        school_id=fixtures.SCHOOL_B,
        section_id=C1,
        on=datetime(2026, 7, 15).date(),
        slot_code="P1",
    )

    assert api.get(f"/sessions/{theirs}").status_code == 404


def test_another_school_s_calendar_exception_does_not_affect_this_school(api, published):
    from modules.timetable.models import CalendarException

    CalendarException.objects.create(
        school_id=fixtures.SCHOOL_B,
        date="2026-07-15",
        kind="holiday",
        reason_key="timetable.reason.holiday",
        version=1,
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
        updated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    days = api.get(f"/calendar?from_date={WEDNESDAY}&to_date={WEDNESDAY}").json()["days"]

    assert days[0]["is_school_day"] is True


def test_a_client_asserted_school_header_is_rejected_outright(api, published):
    """Silently ignoring a spoofed header hides an attack and a bug equally well."""
    response = api.get(
        f"/timetables/current?section_id={C1}&date={WEDNESDAY}",
        HTTP_X_SCHOOL_ID=str(fixtures.SCHOOL_B),
    )

    assert response.status_code == 400
    assert response.json()["message_key"] == "error.client_asserted_identity"


# --- step-up on publication ------------------------------------------------


def test_publishing_with_a_stale_second_factor_is_refused(api, draft, context_factory):
    """Exercised at the service, because the persona always asserts 2FA just now."""
    from modules.timetable.api.deps import publication_service

    stale = context_factory(fixtures.TEACHER_T1, auth_age=timedelta(minutes=30))

    with pytest.raises(StaleAuth):
        publication_service().publish(
            stale, timetable_id=uuid.UUID(draft["id"]), expected_version=draft["version"]
        )

    assert api.get(f"/timetables/{draft['id']}").json()["state"] == "draft"


def test_publishing_without_any_second_factor_is_refused(api, draft, context_factory):
    from modules.timetable.api.deps import publication_service

    password_only = context_factory(fixtures.TEACHER_T1, auth_level=AuthLevel.PASSWORD)

    with pytest.raises(StaleAuth):
        publication_service().publish(
            password_only,
            timetable_id=uuid.UUID(draft["id"]),
            expected_version=draft["version"],
        )
