"""ScopeFacts/RelationshipFacts separation, and the value primitives."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, date, datetime

import pytest

from contracts.identity import AuthLevel, RequestContext
from contracts.scope import Relationship, RelationshipFacts, ScopeFacts
from contracts.values import (
    SCHOOL_TIMEZONE,
    paise_from_rupee_string,
    rupee_string_from_paise,
    school_date,
    validate_marks_string,
)

pytestmark = pytest.mark.contract


def test_relationship_facts_is_a_separate_dto_from_scope_facts():
    # The separation is what prevents a recursive Access->Registry->Access call.
    assert RelationshipFacts is not ScopeFacts
    assert not hasattr(RelationshipFacts, "resource_school_id")


def test_scope_facts_requires_resource_school_id():
    with pytest.raises(TypeError):
        ScopeFacts()  # type: ignore[call-arg]


def test_from_relationship_folds_registry_answer_into_scope():
    actor, subject, school, section = (uuid.uuid4() for _ in range(4))
    facts = RelationshipFacts(
        actor_id=actor,
        subject_person_id=subject,
        relationship=Relationship.GUARDIAN,
        section_id=section,
        effective_date=date(2026, 7, 15),
    )
    scope = ScopeFacts.from_relationship(resource_school_id=school, facts=facts)
    assert scope.resource_school_id == school
    assert scope.relationship is Relationship.GUARDIAN
    assert scope.subject_person_id == subject
    assert scope.section_id == section
    assert scope.effective_date == date(2026, 7, 15)


def test_scope_facts_optional_fields_default_to_none():
    scope = ScopeFacts(resource_school_id=uuid.uuid4())
    assert scope.subject_person_id is None
    assert scope.section_id is None
    assert scope.subject_id is None
    assert scope.relationship is None
    assert scope.effective_date is None


def test_relationship_values_are_stable():
    assert [r.value for r in Relationship] == [
        "none",
        "self",
        "guardian",
        "assigned_teacher",
        "class_teacher",
    ]


def test_auth_levels_are_ordered_by_strength():
    assert AuthLevel.ANONYMOUS.rank < AuthLevel.PASSWORD.rank < AuthLevel.TWO_FACTOR.rank


def test_request_context_rejects_naive_auth_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        RequestContext(
            actor_id=uuid.uuid4(),
            school_id=uuid.uuid4(),
            request_id="r",
            auth_level=AuthLevel.PASSWORD,
            auth_time=datetime(2026, 7, 15, 4, 30),
        )


def test_request_context_is_immutable():
    context = RequestContext(
        actor_id=uuid.uuid4(),
        school_id=uuid.uuid4(),
        request_id="r",
        auth_level=AuthLevel.PASSWORD,
        auth_time=datetime.now(UTC),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.school_id = uuid.uuid4()  # type: ignore[misc]


# --- money -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "paise"),
    [("0", 0), ("1", 100), ("1250.50", 125050), ("0.01", 1), ("99999.99", 9999999)],
)
def test_rupee_strings_parse_to_integer_paise(text, paise):
    assert paise_from_rupee_string(text) == paise


@pytest.mark.parametrize("bad", ["1250.505", "abc", "", "1,250.50", "₹10"])
def test_sub_paise_precision_and_junk_are_refused_never_rounded(bad):
    with pytest.raises(ValueError):
        paise_from_rupee_string(bad)


def test_paise_render_back_to_two_decimals():
    assert rupee_string_from_paise(125050) == "1250.50"
    assert rupee_string_from_paise(1) == "0.01"


def test_money_round_trips_without_float_error():
    for text in ("0.01", "1250.50", "99999.99", "12345.67"):
        assert rupee_string_from_paise(paise_from_rupee_string(text)) == text


# --- marks -----------------------------------------------------------------


@pytest.mark.parametrize("text", ["0", "8.5", "80", "79.25", "100.00"])
def test_valid_marks_pass_through_as_strings(text):
    # Strings, not floats: 8.5 must not become 8.499999999999999 in the browser.
    assert validate_marks_string(text) == text
    assert isinstance(validate_marks_string(text), str)


@pytest.mark.parametrize("bad", ["-1", "8.555", "nan", "inf", "abc", ""])
def test_invalid_marks_are_refused(bad):
    with pytest.raises(ValueError):
        validate_marks_string(bad)


# --- time ------------------------------------------------------------------


def test_school_timezone_is_asia_kolkata():
    assert str(SCHOOL_TIMEZONE) == "Asia/Kolkata"


def test_late_utc_evening_is_the_next_school_day():
    # 19:00 UTC on 30 June is 00:30 IST on 1 July. Attendance must agree with
    # the school, not with UTC.
    assert school_date(datetime(2026, 6, 30, 19, 0, tzinfo=UTC)) == date(2026, 7, 1)


def test_early_utc_morning_is_the_same_school_day():
    assert school_date(datetime(2026, 6, 30, 4, 30, tzinfo=UTC)) == date(2026, 6, 30)


def test_school_date_rejects_naive_instants():
    with pytest.raises(ValueError, match="timezone-aware"):
        school_date(datetime(2026, 6, 30, 19, 0))
