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
from contracts.scope import Relationship, RelationshipFacts

from .. import fixtures
from .failures import FailureInjector


class FakeRegistry:
    """Fixture-backed RegistryPort implementation.

    Relationship resolution is pure table lookup over
    ``shared.fixtures``: G1 guards S1/S2, G2 guards only S3, T1 is class teacher
    of C1, T2 is unassigned. Anything else resolves to Relationship.NONE.
    """

    def __init__(self, *, failures: FailureInjector | None = None) -> None:
        """Build the adapter with optional failure injection."""
        self._failures = failures or FailureInjector()

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

        members = [
            student for student, section in fixtures.SECTION_MEMBERSHIP if section == section_id
        ]
        if subject_id is not None:
            members = [
                student
                for student in members
                if subject_id in SUBJECT_ENROLMENTS.get(student, ())
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
        return replace(
            facts,
            school_id=_school_of(student_id),
            effective_date=effective_date,
            subject_ids=tuple(SUBJECT_ENROLMENTS.get(student_id, ())),
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
