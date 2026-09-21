"""In-process RegistryPort implementation over M02 tables.

Delegates roster and dating helpers to the enrolment and relationship services
so REST and port consumers cannot disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from django.db.models import Q

from contracts.errors import ObjectInaccessible
from contracts.identity import RequestContext
from contracts.people import (
    RosterDTO,
    StudentDTO,
    StudentStatus,
)
from contracts.people import (
    TeachingAssignment as TeachingAssignmentDTO,
)
from contracts.ports_registry import SchoolProfileDTO, TermDTO
from contracts.scope import Relationship, RelationshipFacts

from ..models import (
    Enrolment,
    Guardian,
    GuardianLink,
    SchoolConfig,
    Section,
    StaffProfile,
    Student,
    Subject,
    Term,
)
from ..models import TeachingAssignment as TeachingAssignmentRow
from .effective import range_covers
from .enrolments import (
    active_section_for_student,
    assemble_roster,
    subject_ids_for_student,
)
from .guardian_links import GuardianLinkService
from .teaching_assignments import TeachingAssignmentService


@dataclass(frozen=True, slots=True)
class RegistryService:
    """Concrete RegistryPort for in-process consumers.

    Read-only. Authorisation of the caller is the consumer's responsibility
    via Access; this port only answers school-scoped facts.
    """

    clock: object

    def get_student(self, context: RequestContext, student_id: UUID) -> StudentDTO:
        """Return one student. Cross-school and missing ids are indistinguishable."""
        row = Student.objects.filter(id=student_id, school_id=context.school_id).first()
        if row is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return StudentDTO(
            id=row.id,
            school_id=row.school_id,
            admission_no=row.admission_no,
            display_name=row.display_name,
            status=StudentStatus(row.status),
        )

    def person_kind(self, context: RequestContext, person_id: UUID) -> str:
        """Return the kind of Registry person, or raise ObjectInaccessible.

        Archived people still resolve: an archived guardian's account is
        deactivated by the school, not made unknowable here.
        """
        if Student.objects.filter(id=person_id, school_id=context.school_id).exists():
            return "student"
        if Guardian.objects.filter(id=person_id, school_id=context.school_id).exists():
            return "guardian"
        if StaffProfile.objects.filter(id=person_id, school_id=context.school_id).exists():
            return "staff"
        raise ObjectInaccessible("error.object_inaccessible")

    def current_term(self, context: RequestContext, on: date) -> TermDTO | None:
        """Return the unarchived term containing ``on``, earliest start first."""
        row = (
            Term.objects.filter(
                school_id=context.school_id, archived=False, start__lte=on, end__gte=on
            )
            .order_by("start")
            .first()
        )
        if row is None:
            return None
        return TermDTO(
            id=row.id, year_id=row.year_id, name=row.name, start=row.start, end=row.end
        )

    def active_student_ids(self, context: RequestContext, on: date) -> tuple[UUID, ...]:
        """Return pupils with an active enrolment covering ``on``, sorted for stability."""
        rows = (
            Enrolment.objects.filter(
                school_id=context.school_id, state="active", from_date__lte=on
            )
            .filter(Q(to_date__isnull=True) | Q(to_date__gte=on))
            .values_list("student_id", flat=True)
            .distinct()
        )
        return tuple(sorted(set(rows), key=str))

    def latest_standard(self, context: RequestContext, student_id: UUID) -> int | None:
        """Return the standard number of the pupil's latest enrolment, if any."""
        row = (
            Enrolment.objects.filter(school_id=context.school_id, student_id=student_id)
            .select_related("section__standard")
            .order_by("-from_date", "-created_at")
            .first()
        )
        return row.section.standard.number if row is not None else None

    def linked_student_ids(
        self, context: RequestContext, person_id: UUID, on: date
    ) -> tuple[UUID, ...]:
        """Return the pupil themselves, or a guardian's children linked on ``on``."""
        if Student.objects.filter(id=person_id, school_id=context.school_id).exists():
            return (person_id,)
        rows = (
            GuardianLink.objects.filter(
                school_id=context.school_id,
                guardian_id=person_id,
                visibility="academic",
                from_date__lte=on,
            )
            .filter(Q(to_date__isnull=True) | Q(to_date__gte=on))
            .values_list("student_id", flat=True)
        )
        return tuple(sorted(set(rows), key=str))

    def display_names(self, context: RequestContext, ids: tuple[UUID, ...]) -> dict[UUID, str]:
        """Return {person id: display name} across students, guardians and staff."""
        wanted = set(ids)
        names: dict[UUID, str] = {}
        for model in (Student, Guardian, StaffProfile):
            names.update(
                model.objects.filter(school_id=context.school_id, id__in=wanted).values_list(
                    "id", "display_name"
                )
            )
        return names

    def school_profile(self, context: RequestContext) -> SchoolProfileDTO | None:
        """Return the installed SchoolConfig as a DTO, or None."""
        row = SchoolConfig.objects.filter(school_id=context.school_id).first()
        if row is None:
            return None
        return SchoolProfileDTO(
            display_name=row.display_name, board=row.board, settings=dict(row.settings or {})
        )

    def subject_names(self, context: RequestContext) -> dict[UUID, str]:
        """Return {subject id: display name} for the school, archived included."""
        return dict(
            Subject.objects.filter(school_id=context.school_id).values_list(
                "id", "display_name"
            )
        )

    def section_label(self, context: RequestContext, section_id: UUID) -> str | None:
        """Return "Std N - name" for a section of this school."""
        row = (
            Section.objects.filter(id=section_id, school_id=context.school_id)
            .select_related("standard")
            .first()
        )
        return f"Std {row.standard.number} - {row.name}" if row is not None else None

    def get_roster(
        self,
        context: RequestContext,
        section_id: UUID,
        effective_date: date,
        subject_id: UUID | None = None,
    ) -> RosterDTO:
        """Return pupils enrolled in a section on a date, optionally by subject."""
        section = Section.objects.filter(id=section_id, school_id=context.school_id).first()
        if section is None:
            raise ObjectInaccessible("error.object_inaccessible")
        return assemble_roster(
            school_id=context.school_id,
            section=section,
            effective_date=effective_date,
            subject_id=subject_id,
        )

    def get_relationships(
        self,
        context: RequestContext,
        actor_id: UUID,
        student_id: UUID,
        effective_date: date,
    ) -> RelationshipFacts:
        """Return dated relationship facts between an actor and a student."""
        probe = replace(context, actor_id=actor_id)
        facts = self.relationship_facts(probe, student_id)
        subject_ids = subject_ids_for_student(
            school_id=context.school_id,
            student_id=student_id,
            effective_date=effective_date,
        )
        link = GuardianLinkService.active_guardian_link(
            school_id=context.school_id,
            guardian_id=actor_id,
            student_id=student_id,
            effective_date=effective_date,
        )
        valid_until = (
            link.to_date if link is not None and link.visibility == "academic" else None
        )
        section_id = active_section_for_student(
            school_id=context.school_id,
            student_id=student_id,
            effective_date=effective_date,
        )
        return replace(
            facts,
            school_id=context.school_id,
            effective_date=effective_date,
            subject_ids=subject_ids,
            valid_until=valid_until,
            section_id=section_id or facts.section_id,
            section_ids=(section_id,) if section_id is not None else facts.section_ids,
        )

    def get_teaching_assignments(
        self,
        context: RequestContext,
        staff_id: UUID,
        effective_date: date,
    ) -> tuple[TeachingAssignmentDTO, ...]:
        """Return assignments in force for a staff member on a date."""
        rows = TeachingAssignmentService.assignments_for_staff(
            school_id=context.school_id,
            staff_id=staff_id,
            effective_date=effective_date,
        )
        return tuple(
            TeachingAssignmentDTO(
                section_id=row.section_id,
                subject_id=row.subject_id,
                from_date=row.from_date,
                to_date=row.to_date,
            )
            for row in rows
        )

    def relationship_facts(
        self,
        context: RequestContext,
        subject_person_id: UUID,
    ) -> RelationshipFacts:
        """Return how the context actor relates to the subject person.

        Returns NONE rather than raising when unrelated or cross-school. Uses the
        injected clock's school-local date as the effective date.
        """
        actor = context.actor_id
        student = Student.objects.filter(
            id=subject_person_id, school_id=context.school_id
        ).first()
        if student is None:
            return RelationshipFacts(
                actor_id=actor,
                subject_person_id=subject_person_id,
                relationship=Relationship.NONE,
                school_id=context.school_id,
            )

        probe_date = self.clock.now().date()
        section_id = active_section_for_student(
            school_id=context.school_id,
            student_id=subject_person_id,
            effective_date=probe_date,
        )
        section_ids = (section_id,) if section_id is not None else ()

        if actor == subject_person_id:
            relationship = Relationship.SELF
        else:
            guardian_link = GuardianLinkService.active_guardian_link(
                school_id=context.school_id,
                guardian_id=actor,
                student_id=subject_person_id,
                effective_date=probe_date,
            )
            if guardian_link is not None and guardian_link.visibility == "academic":
                relationship = Relationship.GUARDIAN
            elif section_ids and any(
                row.is_class_teacher
                for row in TeachingAssignmentRow.objects.filter(
                    school_id=context.school_id,
                    staff_id=actor,
                    section_id__in=section_ids,
                )
                if range_covers(
                    from_date=row.from_date, to_date=row.to_date, effective_date=probe_date
                )
            ):
                relationship = Relationship.CLASS_TEACHER
            elif section_ids:
                matching = [
                    row
                    for row in TeachingAssignmentService.assignments_for_staff(
                        school_id=context.school_id,
                        staff_id=actor,
                        effective_date=probe_date,
                    )
                    if row.section_id in section_ids
                ]
                relationship = Relationship.ASSIGNED_TEACHER if matching else Relationship.NONE
            else:
                relationship = Relationship.NONE

        return RelationshipFacts(
            actor_id=actor,
            subject_person_id=subject_person_id,
            relationship=relationship,
            section_id=section_id,
            school_id=context.school_id,
            section_ids=section_ids,
            effective_date=probe_date,
        )


def registry_service() -> RegistryService:
    """Return a RegistryService instance for host and deps wiring."""
    from django.conf import settings

    return RegistryService(clock=settings.SCHOOL_CLOCK)
