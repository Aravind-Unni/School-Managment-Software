"""The deny-by-default authorisation matrix, asserted persona by persona.

This is the table every business module must reproduce for its own actions. It
is here so that a regression in the shared Access/Registry/resolver path is
caught by the foundation suite rather than by fourteen module suites.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from contracts.errors import ActionDenied, ObjectInaccessible, StaleAuth
from contracts.identity import AuthLevel
from contracts.scope import Relationship
from shared import fixtures

ACTION_LIST = "demo.list_notes"
ACTION_READ = "demo.read_note"
ACTION_WRITE = "demo.write_note"


# --- relationship resolution ----------------------------------------------


def test_g1_is_guardian_of_s1(resolver, guardian_g1_context):
    facts = resolver.facts_for_subject(
        guardian_g1_context, subject_person_id=fixtures.STUDENT_S1
    )
    assert facts.relationship is Relationship.GUARDIAN


def test_g1_is_guardian_of_s2_too(resolver, guardian_g1_context):
    facts = resolver.facts_for_subject(
        guardian_g1_context, subject_person_id=fixtures.STUDENT_S2
    )
    assert facts.relationship is Relationship.GUARDIAN


def test_g2_is_unrelated_to_s1(resolver, guardian_g2_context):
    # The required negative case: G2 guards S3, not S1.
    facts = resolver.facts_for_subject(
        guardian_g2_context, subject_person_id=fixtures.STUDENT_S1
    )
    assert facts.relationship is Relationship.NONE


def test_t1_is_class_teacher_of_s1s_section(resolver, teacher_t1_context):
    facts = resolver.facts_for_subject(
        teacher_t1_context, subject_person_id=fixtures.STUDENT_S1
    )
    assert facts.relationship is Relationship.CLASS_TEACHER
    assert facts.section_id == fixtures.CLASS_C1


def test_t2_is_unassigned(resolver, teacher_t2_context):
    facts = resolver.facts_for_subject(
        teacher_t2_context, subject_person_id=fixtures.STUDENT_S1
    )
    assert facts.relationship is Relationship.NONE


def test_a_student_reading_their_own_record_resolves_to_self(resolver, context_factory):
    context = context_factory(fixtures.STUDENT_S1)
    facts = resolver.facts_for_subject(context, subject_person_id=fixtures.STUDENT_S1)
    assert facts.relationship is Relationship.SELF


# --- the read matrix -------------------------------------------------------


@pytest.mark.parametrize(
    ("persona", "subject", "allowed"),
    [
        (fixtures.STUDENT_S1, fixtures.STUDENT_S1, True),  # self
        (fixtures.GUARDIAN_G1, fixtures.STUDENT_S1, True),  # guardian
        (fixtures.GUARDIAN_G1, fixtures.STUDENT_S2, True),  # guardian, 2nd child
        (fixtures.GUARDIAN_G2, fixtures.STUDENT_S1, False),  # unrelated guardian
        (fixtures.TEACHER_T1, fixtures.STUDENT_S1, True),  # assigned teacher
        (fixtures.TEACHER_T2, fixtures.STUDENT_S1, False),  # unassigned teacher
        (fixtures.STUDENT_S3, fixtures.STUDENT_S1, False),  # another student
    ],
)
def test_read_matrix(resolver, context_factory, persona, subject, allowed):
    context = context_factory(persona)
    if allowed:
        resolver.require(context, ACTION_READ, subject_person_id=subject)
    else:
        with pytest.raises(ActionDenied):
            resolver.require(context, ACTION_READ, subject_person_id=subject)


# --- the write matrix ------------------------------------------------------


@pytest.mark.parametrize(
    ("persona", "allowed"),
    [
        (fixtures.TEACHER_T1, True),  # assigned teacher, fresh 2FA
        (fixtures.TEACHER_T2, False),  # unassigned
        (fixtures.GUARDIAN_G1, False),  # may read, must not write
        (fixtures.STUDENT_S1, False),  # subject may read, must not write
    ],
)
def test_write_matrix(resolver, context_factory, persona, allowed):
    context = context_factory(persona)
    if allowed:
        resolver.require(context, ACTION_WRITE, subject_person_id=fixtures.STUDENT_S1)
    else:
        with pytest.raises(ActionDenied):
            resolver.require(context, ACTION_WRITE, subject_person_id=fixtures.STUDENT_S1)


# --- deny by default -------------------------------------------------------


@pytest.mark.parametrize(
    "unknown_action",
    ["demo.delete_everything", "demo.read", "fees.read_invoice", "", "demo.list_notes_v2"],
)
def test_an_action_with_no_rule_is_denied(resolver, teacher_t1_context, unknown_action):
    # No allow rule means deny. There is no allow_all anywhere.
    with pytest.raises(ActionDenied):
        resolver.require(teacher_t1_context, unknown_action)


# --- tenant isolation ------------------------------------------------------


def test_cross_school_access_is_404_not_403(resolver, teacher_t1_context):
    # 404, so a probe cannot tell "exists but not yours" from "does not exist".
    with pytest.raises(ObjectInaccessible):
        resolver.require(
            teacher_t1_context,
            ACTION_READ,
            subject_person_id=fixtures.STUDENT_S1,
            resource_school_id=fixtures.SCHOOL_B,
        )


def test_school_check_precedes_the_permission_check(resolver, teacher_t2_context):
    # T2 would be a 403 in their own school; in another school it must be 404,
    # proving school is evaluated first.
    with pytest.raises(ObjectInaccessible):
        resolver.require(
            teacher_t2_context,
            ACTION_READ,
            subject_person_id=fixtures.STUDENT_S1,
            resource_school_id=fixtures.SCHOOL_B,
        )


# --- 2FA freshness ---------------------------------------------------------


def test_stale_two_factor_is_401_on_a_write(resolver, context_factory):
    context = context_factory(fixtures.TEACHER_T1, auth_age=timedelta(minutes=16))
    with pytest.raises(StaleAuth) as raised:
        resolver.require(context, ACTION_WRITE, subject_person_id=fixtures.STUDENT_S1)
    assert raised.value.message_key == "error.two_factor_stale"
    assert raised.value.http_status == 401


def test_fresh_two_factor_passes_the_same_write(resolver, context_factory):
    context = context_factory(fixtures.TEACHER_T1, auth_age=timedelta(minutes=14))
    resolver.require(context, ACTION_WRITE, subject_person_id=fixtures.STUDENT_S1)


def test_password_only_is_401_on_a_write(resolver, context_factory):
    context = context_factory(fixtures.TEACHER_T1, auth_level=AuthLevel.PASSWORD)
    with pytest.raises(StaleAuth) as raised:
        resolver.require(context, ACTION_WRITE, subject_person_id=fixtures.STUDENT_S1)
    assert raised.value.message_key == "error.two_factor_required"


def test_password_only_still_permits_a_read(resolver, context_factory):
    # Reads do not demand 2FA; only the write rule does.
    context = context_factory(fixtures.GUARDIAN_G1, auth_level=AuthLevel.PASSWORD)
    resolver.require(context, ACTION_READ, subject_person_id=fixtures.STUDENT_S1)


def test_stale_two_factor_does_not_block_a_read(resolver, context_factory):
    context = context_factory(fixtures.GUARDIAN_G1, auth_age=timedelta(days=30))
    resolver.require(context, ACTION_READ, subject_person_id=fixtures.STUDENT_S1)


# --- school-scoped actions -------------------------------------------------


def test_listing_is_school_scoped_and_needs_no_relationship(resolver, teacher_t2_context):
    # T2 is unassigned, so has no relationship to anyone, yet may still list.
    resolver.require(teacher_t2_context, ACTION_LIST)


def test_listing_in_another_school_is_still_404(resolver, teacher_t1_context):
    with pytest.raises(ObjectInaccessible):
        resolver.require(teacher_t1_context, ACTION_LIST, resource_school_id=fixtures.SCHOOL_B)


# --- navigation helper ----------------------------------------------------


def test_allows_returns_false_instead_of_raising(resolver, guardian_g2_context):
    assert (
        resolver.allows(guardian_g2_context, ACTION_READ, subject_person_id=fixtures.STUDENT_S1)
        is False
    )


def test_allows_returns_true_when_permitted(resolver, guardian_g1_context):
    assert (
        resolver.allows(guardian_g1_context, ACTION_READ, subject_person_id=fixtures.STUDENT_S1)
        is True
    )


# --- failure injection ---------------------------------------------------


def test_registry_failure_propagates_rather_than_silently_allowing(
    context_factory, fake_access, failures
):
    from shared.fakes import FakeRegistry, InjectedFailure
    from shared.scope_resolver import ScopeResolver

    failures.fail("registry.relationship_facts", on_call=1)
    resolver = ScopeResolver(access=fake_access, registry=FakeRegistry(failures=failures))
    # A dependency failure must never degrade into an allow.
    with pytest.raises(InjectedFailure):
        resolver.require(
            context_factory(fixtures.TEACHER_T1),
            ACTION_READ,
            subject_person_id=fixtures.STUDENT_S1,
        )
