"""RegistryPort: people, sections, terms and relationships. Owned by M02.

Split from ``contracts/ports.py`` (which re-exports it) to keep each contract
file small. Protocol only -- no implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from .identity import RequestContext
from .people import RosterDTO, StudentDTO, TeachingAssignment
from .scope import RelationshipFacts


@dataclass(frozen=True, slots=True)
class SchoolProfileDTO:
    """The school's name and the settings installed from its config file."""

    display_name: str
    board: str
    settings: dict


@dataclass(frozen=True, slots=True)
class TermDTO:
    """One dated term of an academic year. Both bounds inclusive."""

    id: UUID
    year_id: UUID
    name: str
    start: date
    end: date


@runtime_checkable
class RegistryPort(Protocol):
    """People, sections and relationships. Owned by M02 registry.

    Extended additively for M01. Every method is read-only: no consumer may
    mutate Registry state through this port.
    """

    def get_student(
        self,
        context: RequestContext,
        student_id: UUID,
    ) -> StudentDTO:
        """Return one student.

        Raises ObjectInaccessible (404) for an unknown student AND for one in
        another school, deliberately conflating them so cross-tenant probing
        cannot tell the difference.
        """
        ...

    def person_kind(self, context: RequestContext, person_id: UUID) -> str:
        """Return "student", "guardian" or "staff" for a person of the caller's school.

        Raises ObjectInaccessible (404) for an unknown id AND for a person in
        another school. Used to decide whether an actor is staff or a guardian
        without trusting anything the client says about itself.
        """
        ...

    def current_term(self, context: RequestContext, on: date) -> TermDTO | None:
        """Return the school's term containing ``on``, or None between terms."""
        ...

    def active_student_ids(self, context: RequestContext, on: date) -> tuple[UUID, ...]:
        """Return every pupil with an active enrolment in the school on ``on``."""
        ...

    def latest_standard(self, context: RequestContext, student_id: UUID) -> int | None:
        """Return the standard (1-12) of the pupil's most recent enrolment, or None."""
        ...

    def school_profile(self, context: RequestContext) -> SchoolProfileDTO | None:
        """Return the school's name and settings, or None before installation."""
        ...

    def subject_names(self, context: RequestContext) -> dict[UUID, str]:
        """Return every subject's display name, keyed by subject id."""
        ...

    def section_label(self, context: RequestContext, section_id: UUID) -> str | None:
        """Return a section's label such as "Std 5 - A", or None if unknown."""
        ...

    def get_roster(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
        subject_id: UUID | None = None,
    ) -> RosterDTO:
        """Return the pupils in a section on a date.

        When ``subject_id`` is supplied, only pupils enrolled in that subject
        offering on that date are included, and that filtered roster is the one a
        timetable period must use.

        Does not handle: authorising the caller to see the section. Ask Access.
        """
        ...

    def get_relationships(
        self,
        context: RequestContext,
        actor_id: UUID,
        student_id: UUID,
        effective_date: date,
    ) -> RelationshipFacts:
        """Return how an actor relates to a student on a date.

        Dated because a guardianship or a posting can lapse. Returns
        Relationship.NONE rather than raising when unrelated, because 'unrelated'
        is a normal policy input.
        """
        ...

    def get_teaching_assignments(
        self,
        context: RequestContext,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[TeachingAssignment, ...]:
        """Return the assignments in force for a staff member on a date.

        Returns an empty tuple for an unassigned staff member -- not an error,
        because 'teaches nothing today' is a legitimate state.
        """
        ...

    def relationship_facts(
        self,
        context: RequestContext,
        subject_person_id: UUID,
    ) -> RelationshipFacts:
        """Return how the context's actor relates to the subject person.

        Returns Relationship.NONE rather than raising when unrelated, because
        'unrelated' is a normal policy input, not an error.

        Does not handle: authorising the caller to see the subject. The caller
        folds this into ScopeFacts and asks Access.
        """
        ...
