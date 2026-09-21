"""Deterministic fake Registry adapter.

Answers only RelationshipFacts, from the committed fixture set. It deliberately
exposes nothing else: the narrower this fake is, the harder it is for a module
to grow a hidden dependency on Registry internals.

Does not handle: person or section CRUD. That is M02's real implementation.
"""

from __future__ import annotations

import hashlib
from datetime import date
from uuid import UUID

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.people import (
    RosterDTO,
    RosterEntry,
    StudentDTO,
    StudentStatus,
    TeachingAssignment,
)
from contracts.ports_registry import SchoolProfileDTO, TermDTO
from contracts.scope import Relationship, RelationshipFacts

from .. import fixtures
from .failures import FailureInjector

#: contracts/M10 and M11 scenario "unrelated actor" id.
SCENARIO_UNRELATED_PARENT = UUID("7b302c8c-0ec6-5c7f-d701-e4f998e15110")

#: The term id the M05/M06 fixtures publish results under.
FIXTURE_TERM_ID = UUID("f76bcdb0-b6b9-5a80-a449-a8a4e423716a")


class FakeRegistry:
    """Fixture-backed RegistryPort implementation.

    Relationship resolution is pure table lookup over
    ``shared.fixtures``: G1 guards S1/S2, G2 guards only S3, T1 is class teacher
    of C1, T2 is unassigned. Anything else resolves to Relationship.NONE.

    ``enrolment_overlay`` and ``section_membership_overlay`` let M04 (and later
    modules) supply a scenario-specific cast without rewriting the default table
    M03 tests rely on.
    """

    def __init__(
        self,
        *,
        failures: FailureInjector | None = None,
        enrolment_overlay: dict[UUID, tuple[UUID, ...]] | None = None,
        section_membership_overlay: tuple[tuple[UUID, UUID], ...] | None = None,
    ) -> None:
        """Build the adapter with optional failure injection and scenario overlays."""
        self._failures = failures or FailureInjector()
        self._enrolment_overlay = enrolment_overlay
        self._section_membership_overlay = section_membership_overlay

    def person_kind(self, context: RequestContext, person_id: UUID) -> str:
        """Return the fixture person's kind, or raise ObjectInaccessible.

        School A's synthetic cast only; School B people resolve as absent from
        School A and vice versa, like the real adapter.
        """
        self._failures.maybe_fail("registry.person_kind")
        kinds = {
            fixtures.SCHOOL_A: {
                fixtures.STUDENT_S1: "student",
                fixtures.STUDENT_S2: "student",
                fixtures.STUDENT_S3: "student",
                fixtures.GUARDIAN_G1: "guardian",
                fixtures.GUARDIAN_G2: "guardian",
                fixtures.TEACHER_T1: "staff",
                fixtures.TEACHER_T2: "staff",
                fixtures.TEACHER_T3: "staff",
                fixtures.PRINCIPAL_P1: "staff",
                # The M10/M11 scenarios' "unrelated actor": a parent with no
                # link to any fixture pupil. Real Access denies such an account
                # staff actions by grant; this lets modules test the same.
                SCENARIO_UNRELATED_PARENT: "guardian",
            },
            fixtures.SCHOOL_B: {
                fixtures.STUDENT_S1_SCHOOL_B: "student",
                fixtures.TEACHER_T1_SCHOOL_B: "staff",
            },
        }
        kind = kinds.get(context.school_id, {}).get(person_id)
        if kind is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return kind

    def current_term(self, context: RequestContext, on: date) -> TermDTO | None:
        """Return the one fixture term when ``on`` falls inside it."""
        self._failures.maybe_fail("registry.current_term")
        if context.school_id not in (fixtures.SCHOOL_A, fixtures.SCHOOL_B):
            return None
        if not fixtures.TERM_START <= on <= fixtures.TERM_END:
            return None
        return TermDTO(
            id=FIXTURE_TERM_ID,
            year_id=fixtures.fixture_uuid("school_a.year"),
            name="Term 1",
            start=fixtures.TERM_START,
            end=fixtures.TERM_END,
        )

    def active_student_ids(self, context: RequestContext, on: date) -> tuple[UUID, ...]:
        """Return the fixture pupils of the caller's school."""
        self._failures.maybe_fail("registry.active_student_ids")
        if context.school_id == fixtures.SCHOOL_A:
            return (fixtures.STUDENT_S1, fixtures.STUDENT_S2, fixtures.STUDENT_S3)
        if context.school_id == fixtures.SCHOOL_B:
            return (fixtures.STUDENT_S1_SCHOOL_B,)
        return ()

    def school_profile(self, context: RequestContext) -> SchoolProfileDTO | None:
        """Return a synthetic school profile with the default CBSE grade bands."""
        self._failures.maybe_fail("registry.school_profile")
        return SchoolProfileDTO(
            display_name="Synthetic School",
            board="CBSE",
            settings={
                "grading_bands": [
                    {"grade": grade, "min_percent": minimum}
                    for grade, minimum in (
                        ("A1", 91),
                        ("A2", 81),
                        ("B1", 71),
                        ("B2", 61),
                        ("C1", 51),
                        ("C2", 41),
                        ("D", 33),
                        ("E", 0),
                    )
                ]
            },
        )

    def subject_names(self, context: RequestContext) -> dict[UUID, str]:
        """Return the fixture subjects' names."""
        self._failures.maybe_fail("registry.subject_names")
        return {
            fixtures.SUBJECT_MATHS: "Mathematics",
            fixtures.SUBJECT_MALAYALAM: "Malayalam",
            fixtures.SUBJECT_ENGLISH: "English",
        }

    def section_label(self, context: RequestContext, section_id: UUID) -> str | None:
        """Return the fixture section label."""
        self._failures.maybe_fail("registry.section_label")
        return {fixtures.CLASS_C1: "Std 5 - C1", fixtures.CLASS_C2: "Std 5 - C2"}.get(
            section_id
        )

    def latest_standard(self, context: RequestContext, student_id: UUID) -> int | None:
        """Return the fixture leaving standard (S1 graduated 12, S2 left in 10)."""
        self._failures.maybe_fail("registry.latest_standard")
        return {fixtures.STUDENT_S1: 12, fixtures.STUDENT_S2: 10}.get(student_id)

    def get_student(
        self,
        context: RequestContext,
        student_id: UUID,
    ) -> StudentDTO:
        """Return one fixture student.

        Raises ObjectInaccessible for an unknown student AND for one belonging to
        another school, conflating the two so cross-tenant probing cannot tell
        them apart.
        """
        self._failures.maybe_fail("registry.get_student")
        school = _school_of(student_id)
        if school is None or school != context.school_id:
            raise ObjectInaccessible("error.object_inaccessible")
        return StudentDTO(
            id=student_id,
            school_id=school,
            admission_no=_admission_no(student_id),
            display_name=fixtures.FIXTURE_LABELS.get(student_id, "Synthetic student"),
            status=StudentStatus.ACTIVE,
        )

    def get_roster(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
        subject_id: UUID | None = None,
    ) -> RosterDTO:
        """Return the fixture roster for a section on a date.

        When ``subject_id`` is given the roster is FILTERED to pupils enrolled in
        that subject offering. The fixtures deliberately give S1 and S2 different
        subject enrolments so a consumer that ignores the filter fails a test
        rather than silently marking attendance for a pupil who does not take the
        subject.
        """
        self._failures.maybe_fail("registry.get_roster")
        if section_id not in (fixtures.CLASS_C1, fixtures.CLASS_C2):
            raise ObjectInaccessible("error.object_inaccessible")

        membership = self._section_membership_overlay or fixtures.SECTION_MEMBERSHIP
        members = [student for student, section in membership if section == section_id]
        enrolments = (
            self._enrolment_overlay
            if self._enrolment_overlay is not None
            else SUBJECT_ENROLMENTS
        )
        if subject_id is not None:
            members = [
                student for student in members if subject_id in enrolments.get(student, ())
            ]
        return RosterDTO(
            section_id=section_id,
            date=effective_date,
            version=1,
            subject_id=subject_id,
            students=tuple(
                RosterEntry(
                    student_id=student,
                    enrolment_id=fixtures.fixture_uuid(f"enrolment.{student}.{section_id}"),
                    display_name=fixtures.FIXTURE_LABELS.get(student, "Synthetic"),
                )
                for student in members
            ),
        )

    def get_relationships(
        self,
        context: RequestContext,
        actor_id: UUID,
        student_id: UUID,
        effective_date: date,
    ) -> RelationshipFacts:
        """Return dated relationship facts between an actor and a student.

        Dated, so a consumer can be tested against a lapsed guardianship. G2's
        link to S3 is given an expiry in the fixtures for exactly that purpose.
        """
        self._failures.maybe_fail("registry.get_relationships")
        from dataclasses import replace

        probe = replace(context, actor_id=actor_id)
        facts = self.relationship_facts(probe, student_id)
        # Like the real adapter, report the pupil's section whatever the
        # actor's relationship; consumers use it to find a pupil's class.
        membership = self._section_membership_overlay or fixtures.SECTION_MEMBERSHIP
        pupil_section = next(
            (section for student, section in membership if student == student_id), None
        )
        return replace(
            facts,
            section_id=facts.section_id or pupil_section,
            school_id=_school_of(student_id),
            effective_date=effective_date,
            subject_ids=tuple(
                (
                    self._enrolment_overlay
                    if self._enrolment_overlay is not None
                    else SUBJECT_ENROLMENTS
                ).get(student_id, ())
            ),
            valid_until=RELATIONSHIP_EXPIRY.get((actor_id, student_id)),
        )

    def get_teaching_assignments(
        self,
        context: RequestContext,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[TeachingAssignment, ...]:
        """Return the assignments in force for a staff member on a date.

        Returns an empty tuple for T2, who is unassigned -- a legitimate state,
        not an error.
        """
        self._failures.maybe_fail("registry.get_teaching_assignments")
        return tuple(
            assignment
            for assignment in TEACHING_ASSIGNMENTS.get(staff_id, ())
            if assignment.covers(effective_date)
        )

    def relationship_facts(
        self,
        context: RequestContext,
        subject_person_id: UUID,
    ) -> RelationshipFacts:
        """Return the fixture relationship between actor and subject.

        Returns NONE rather than raising for an unrelated pair, and also for a
        subject in another school: leaking 'exists but not yours' through a
        different exception type would defeat the 404 rule upstream.

        Does not handle: authorising the caller. The host folds this answer into
        ScopeFacts and asks Access.
        """
        self._failures.maybe_fail("registry.relationship_facts")

        actor = context.actor_id
        membership = self._section_membership_overlay or fixtures.SECTION_MEMBERSHIP
        section_id = None
        for candidate_student, candidate_section in membership:
            if candidate_student == subject_person_id:
                section_id = candidate_section
                break
        if section_id is None:
            section_id = fixtures.section_of(subject_person_id)

        if actor == subject_person_id:
            relationship = Relationship.SELF
        elif fixtures.guards(actor, subject_person_id):
            relationship = Relationship.GUARDIAN
        elif section_id is not None and fixtures.teaches(actor, section_id):
            relationship = (
                Relationship.CLASS_TEACHER
                if any(
                    a.teacher_id == actor and a.section_id == section_id and a.is_class_teacher
                    for a in fixtures.TEACHER_ASSIGNMENTS
                )
                else Relationship.ASSIGNED_TEACHER
            )
        else:
            relationship = Relationship.NONE

        return RelationshipFacts(
            actor_id=actor,
            subject_person_id=subject_person_id,
            relationship=relationship,
            section_id=section_id,
            effective_date=fixtures.TERM_SAMPLE_DATE,
        )


#: Which subjects each fixture pupil is enrolled in. S1 takes both; S2 takes only
#: Malayalam. That asymmetry is what makes a missing subject filter detectable.
SUBJECT_ENROLMENTS: dict[UUID, tuple[UUID, ...]] = {
    fixtures.STUDENT_S1: (fixtures.SUBJECT_MATHS, fixtures.SUBJECT_MALAYALAM),
    fixtures.STUDENT_S2: (fixtures.SUBJECT_MALAYALAM,),
    fixtures.STUDENT_S3: (fixtures.SUBJECT_MATHS,),
}


def m04_baseline_registry_kwargs() -> dict[str, object]:
    """Return FakeRegistry kwargs for the M04 baseline scenario.

    S1 and S2 take maths + english; S3 is on C1 maths only (elective outsider for
    English P2). Does not mutate the default SUBJECT_ENROLMENTS table.
    """
    return {
        "enrolment_overlay": {
            fixtures.STUDENT_S1: (fixtures.SUBJECT_MATHS, fixtures.SUBJECT_ENGLISH),
            fixtures.STUDENT_S2: (fixtures.SUBJECT_MATHS, fixtures.SUBJECT_ENGLISH),
            fixtures.STUDENT_S3: (fixtures.SUBJECT_MATHS,),
        },
        "section_membership_overlay": (
            (fixtures.STUDENT_S1, fixtures.CLASS_C1),
            (fixtures.STUDENT_S2, fixtures.CLASS_C1),
            (fixtures.STUDENT_S3, fixtures.CLASS_C1),
        ),
    }


def m05_baseline_registry_kwargs() -> dict[str, object]:
    """Return FakeRegistry kwargs for the M05 baseline scenario.

    S1 and S2 enrol in maths on C1 so both appear on the marking roster.
    """
    return {
        "enrolment_overlay": {
            fixtures.STUDENT_S1: (fixtures.SUBJECT_MATHS, fixtures.SUBJECT_MALAYALAM),
            fixtures.STUDENT_S2: (fixtures.SUBJECT_MATHS, fixtures.SUBJECT_MALAYALAM),
            fixtures.STUDENT_S3: (fixtures.SUBJECT_MATHS,),
        },
        "section_membership_overlay": (
            (fixtures.STUDENT_S1, fixtures.CLASS_C1),
            (fixtures.STUDENT_S2, fixtures.CLASS_C1),
            (fixtures.STUDENT_S3, fixtures.CLASS_C2),
        ),
    }


def m06_baseline_registry_kwargs() -> dict[str, object]:
    """Return FakeRegistry kwargs for the M06 baseline scenario.

    Same C1 maths enrolment as M05 so performance projections cover S1 and S2.
    """
    return m05_baseline_registry_kwargs()


#: Dated teaching assignments. T1 teaches C1; T2 appears nowhere.
TEACHING_ASSIGNMENTS: dict[UUID, tuple[TeachingAssignment, ...]] = {
    fixtures.TEACHER_T1: (
        TeachingAssignment(
            section_id=fixtures.CLASS_C1,
            subject_id=fixtures.SUBJECT_MATHS,
            from_date=fixtures.TERM_START,
            to_date=fixtures.TERM_END,
        ),
        TeachingAssignment(
            section_id=fixtures.CLASS_C1,
            subject_id=fixtures.SUBJECT_MALAYALAM,
            from_date=fixtures.TERM_START,
            to_date=None,
        ),
    ),
}

#: Relationships that lapse, so a consumer can be tested against an expiry.
RELATIONSHIP_EXPIRY: dict[tuple[UUID, UUID], date] = {
    (fixtures.GUARDIAN_G2, fixtures.STUDENT_S3): fixtures.TERM_END,
}


def _school_of(person_id: UUID) -> UUID | None:
    """Return the fixture school a person belongs to, or None if unknown."""
    school_a = {
        fixtures.STUDENT_S1,
        fixtures.STUDENT_S2,
        fixtures.STUDENT_S3,
        fixtures.GUARDIAN_G1,
        fixtures.GUARDIAN_G2,
        fixtures.TEACHER_T1,
        fixtures.TEACHER_T2,
        fixtures.TEACHER_T3,
        fixtures.PRINCIPAL_P1,
    }
    if person_id in school_a:
        return fixtures.SCHOOL_A
    if person_id in {fixtures.STUDENT_S1_SCHOOL_B, fixtures.TEACHER_T1_SCHOOL_B}:
        return fixtures.SCHOOL_B
    return None


def _admission_no(student_id: UUID) -> str:
    """Return a deterministic synthetic admission number.

    Derived from a SHA-256 of the student id, not from ``hash()``: Python
    randomises string hashing per process (PYTHONHASHSEED), so ``hash()`` would
    hand out a different admission number on every run and quietly break the
    determinism the whole fixture set depends on.
    """
    digest = hashlib.sha256(str(student_id).encode()).hexdigest()
    return f"2026/{int(digest[:8], 16) % 9000 + 1000:04d}"
