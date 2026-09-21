"""Section enrolments, subject enrolments and roster assembly.

Does not handle: promotion batches or withdrawal. Those arrive in step 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import transaction

from contracts.errors import ObjectInaccessible, StateConflict, ValidationFailed
from contracts.identity import RequestContext
from contracts.people import RosterDTO, RosterEntry, StudentStatus
from contracts.scope import ScopeFacts

from ..models import (
    AcademicYear,
    Enrolment,
    Section,
    Student,
    Subject,
    SubjectEnrolment,
    SubjectOffering,
)
from .configuration import require_ordered_dates
from .effective import day_before, range_covers, ranges_overlap
from .subject_defaults import end_open_subject_enrolments, enrol_in_compulsory_subjects
from .writes import fetch_in_school, require_expected_version, stamp_new, stamp_update


@dataclass(frozen=True, slots=True)
class EnrolmentService:
    """Reads and writes enrolments and assembles rosters."""

    access: object
    clock: object

    def _authorise(self, context: RequestContext, action: str) -> None:
        """Ask Access whether this school-scoped action is permitted."""
        self.access.check(context, action, ScopeFacts(resource_school_id=context.school_id))

    def create_enrolment(
        self,
        context: RequestContext,
        *,
        student_id: UUID,
        year_id: UUID,
        section_id: UUID,
        from_date: date,
        to_date: date | None,
    ) -> Enrolment:
        """Enrol a student into a section for a year."""
        self._authorise(context, "registry.manage")
        require_ordered_dates(from_date, to_date or from_date)
        student = fetch_in_school(Student, school_id=context.school_id, row_id=student_id)
        year = fetch_in_school(AcademicYear, school_id=context.school_id, row_id=year_id)
        section = fetch_in_school(Section, school_id=context.school_id, row_id=section_id)
        if section.year_id != year.id:
            raise ValidationFailed("registry.error.referenced_record")
        if year.state in ("closed", "archived"):
            raise StateConflict("registry.error.year_closed")
        if student.archived:
            raise ValidationFailed("registry.error.referenced_record")
        self._refuse_overlapping_enrolment(
            context.school_id,
            student_id=student_id,
            year_id=year_id,
            from_date=from_date,
            to_date=to_date,
        )
        now = self.clock.now()
        row = Enrolment(
            school_id=context.school_id,
            student_id=student_id,
            year_id=year_id,
            section_id=section_id,
            from_date=from_date,
            to_date=to_date,
            state="active",
        )
        with transaction.atomic():
            stamp_new(row, now=now)
            row.save()
            enrol_in_compulsory_subjects(row, from_date=from_date, to_date=to_date, now=now)
        return row

    def transfer_enrolment(
        self,
        context: RequestContext,
        *,
        enrolment_id: UUID,
        target_section_id: UUID,
        effective_date: date,
        expected_version: int,
    ) -> Enrolment:
        """Move a pupil to another section from an effective date onward."""
        self._authorise(context, "students.update")
        target = fetch_in_school(Section, school_id=context.school_id, row_id=target_section_id)
        with transaction.atomic():
            source = fetch_in_school(
                Enrolment, school_id=context.school_id, row_id=enrolment_id, for_update=True
            )
            require_expected_version(source, expected_version)
            if source.state != "active":
                raise StateConflict("registry.error.referenced_record")
            if not range_covers(
                from_date=source.from_date,
                to_date=source.to_date,
                effective_date=effective_date,
            ):
                raise ValidationFailed("registry.error.end_before_start")
            if target.year_id != source.year_id:
                raise ValidationFailed("registry.error.referenced_record")
            if target.id == source.section_id:
                raise ValidationFailed("registry.error.referenced_record")
            remaining_to_date = source.to_date
            source.to_date = day_before(effective_date)
            stamp_update(source, now=self.clock.now())
            source.save()
            end_open_subject_enrolments(
                source, last_day=day_before(effective_date), now=self.clock.now()
            )
            new_row = Enrolment(
                school_id=context.school_id,
                student_id=source.student_id,
                year_id=source.year_id,
                section_id=target_section_id,
                from_date=effective_date,
                to_date=remaining_to_date,
                previous_enrolment_id=source.id,
                state="active",
            )
            stamp_new(new_row, now=self.clock.now())
            new_row.save()
            enrol_in_compulsory_subjects(
                new_row,
                from_date=effective_date,
                to_date=remaining_to_date,
                now=self.clock.now(),
            )
        return new_row

    def list_enrolments(
        self,
        context: RequestContext,
        *,
        student_id: UUID | None,
        after_id: UUID | None,
        page_size: int,
    ) -> tuple[tuple[Enrolment, ...], bool]:
        """Return one cursor page of enrolments."""
        self._authorise(context, "students.read")
        queryset = Enrolment.objects.filter(school_id=context.school_id).order_by("id")
        if student_id is not None:
            fetch_in_school(Student, school_id=context.school_id, row_id=student_id)
            queryset = queryset.filter(student_id=student_id)
        if after_id is not None:
            queryset = queryset.filter(id__gt=after_id)
        rows = tuple(queryset[: page_size + 1])
        return rows[:page_size], len(rows) > page_size

    def create_subject_enrolment(
        self,
        context: RequestContext,
        *,
        enrolment_id: UUID,
        subject_offering_id: UUID,
        from_date: date,
        to_date: date | None,
    ) -> SubjectEnrolment:
        """Enrol a pupil in one subject offering."""
        self._authorise(context, "registry.manage")
        require_ordered_dates(from_date, to_date or from_date)
        enrolment = fetch_in_school(Enrolment, school_id=context.school_id, row_id=enrolment_id)
        offering = fetch_in_school(
            SubjectOffering, school_id=context.school_id, row_id=subject_offering_id
        )
        if enrolment.section_id != offering.section_id:
            raise ValidationFailed("registry.error.referenced_record")
        if offering.archived:
            raise ValidationFailed("registry.error.referenced_record")
        now = self.clock.now()
        row = SubjectEnrolment(
            school_id=context.school_id,
            enrolment_id=enrolment_id,
            subject_offering_id=subject_offering_id,
            from_date=from_date,
            to_date=to_date,
        )
        stamp_new(row, now=now)
        row.save()
        return row

    def end_subject_enrolment(
        self,
        context: RequestContext,
        *,
        subject_enrolment_id: UUID,
        to_date: date,
        expected_version: int,
    ) -> SubjectEnrolment:
        """Set the inclusive end date on a subject enrolment."""
        self._authorise(context, "registry.manage")
        with transaction.atomic():
            row = fetch_in_school(
                SubjectEnrolment,
                school_id=context.school_id,
                row_id=subject_enrolment_id,
                for_update=True,
            )
            require_expected_version(row, expected_version)
            if to_date < row.from_date:
                raise ValidationFailed("registry.error.end_before_start")
            row.to_date = to_date
            stamp_update(row, now=self.clock.now())
            row.save()
        return row

    def list_subject_enrolments(
        self,
        context: RequestContext,
        *,
        enrolment_id: UUID | None,
        after_id: UUID | None,
        page_size: int,
    ) -> tuple[tuple[SubjectEnrolment, ...], bool]:
        """Return one cursor page of subject enrolments."""
        self._authorise(context, "students.read")
        queryset = SubjectEnrolment.objects.filter(school_id=context.school_id).order_by("id")
        if enrolment_id is not None:
            fetch_in_school(Enrolment, school_id=context.school_id, row_id=enrolment_id)
            queryset = queryset.filter(enrolment_id=enrolment_id)
        if after_id is not None:
            queryset = queryset.filter(id__gt=after_id)
        rows = tuple(queryset[: page_size + 1])
        return rows[:page_size], len(rows) > page_size

    def get_section_roster(
        self,
        context: RequestContext,
        *,
        section_id: UUID,
        effective_date: date,
        subject_id: UUID | None,
    ) -> RosterDTO:
        """Return the dated roster for a section, optionally filtered by subject."""
        self._authorise(context, "students.read")
        section = fetch_in_school(Section, school_id=context.school_id, row_id=section_id)
        return assemble_roster(
            school_id=context.school_id,
            section=section,
            effective_date=effective_date,
            subject_id=subject_id,
        )

    def _refuse_overlapping_enrolment(
        self,
        school_id: UUID,
        *,
        student_id: UUID,
        year_id: UUID,
        from_date: date,
        to_date: date | None,
        excluding_id: UUID | None = None,
    ) -> None:
        """Raise when another active enrolment for the same pupil and year overlaps."""
        for existing in Enrolment.objects.filter(
            school_id=school_id,
            student_id=student_id,
            year_id=year_id,
            state="active",
        ):
            if excluding_id is not None and existing.id == excluding_id:
                continue
            if ranges_overlap(
                left_from=from_date,
                left_to=to_date,
                right_from=existing.from_date,
                right_to=existing.to_date,
            ):
                raise StateConflict("registry.error.enrolment_overlap")


def assemble_roster(
    *,
    school_id: UUID,
    section: Section,
    effective_date: date,
    subject_id: UUID | None,
) -> RosterDTO:
    """Build a RosterDTO from stored enrolments without authorisation.

    Shared by the REST path and RegistryPort. Raises ObjectInaccessible when the
    section belongs to another school, matching fetch_in_school semantics.
    """
    if section.school_id != school_id:
        raise ObjectInaccessible("error.object_inaccessible")
    enrolments = [
        row
        for row in Enrolment.objects.filter(
            school_id=school_id, section_id=section.id, state="active"
        )
        if range_covers(
            from_date=row.from_date, to_date=row.to_date, effective_date=effective_date
        )
    ]
    if subject_id is not None:
        fetch_in_school(Subject, school_id=school_id, row_id=subject_id)
        offering_ids = {
            offering.id
            for offering in SubjectOffering.objects.filter(
                school_id=school_id,
                section_id=section.id,
                subject_id=subject_id,
                archived=False,
            )
        }
        allowed_enrolment_ids = {
            subject_row.enrolment_id
            for subject_row in SubjectEnrolment.objects.filter(
                school_id=school_id, subject_offering_id__in=offering_ids
            )
            if range_covers(
                from_date=subject_row.from_date,
                to_date=subject_row.to_date,
                effective_date=effective_date,
            )
        }
        enrolments = [row for row in enrolments if row.id in allowed_enrolment_ids]
    students = {
        row.id: row
        for row in Student.objects.filter(
            id__in=[enrolment.student_id for enrolment in enrolments]
        )
    }
    entries = tuple(
        RosterEntry(
            student_id=enrolment.student_id,
            enrolment_id=enrolment.id,
            display_name=students[enrolment.student_id].display_name,
        )
        for enrolment in sorted(enrolments, key=lambda row: row.student_id)
        if enrolment.student_id in students
        and students[enrolment.student_id].status == StudentStatus.ACTIVE
    )
    version = max((row.version for row in enrolments), default=section.version)
    return RosterDTO(
        section_id=section.id,
        date=effective_date,
        version=version,
        subject_id=subject_id,
        students=entries,
    )


def active_section_for_student(
    *,
    school_id: UUID,
    student_id: UUID,
    effective_date: date,
) -> UUID | None:
    """Return the section a student belongs to on a date, if any."""
    queryset = Enrolment.objects.filter(
        school_id=school_id, student_id=student_id, state="active"
    )
    for row in queryset:
        if range_covers(
            from_date=row.from_date, to_date=row.to_date, effective_date=effective_date
        ):
            return row.section_id
    return None


def subject_ids_for_student(
    *,
    school_id: UUID,
    student_id: UUID,
    effective_date: date,
) -> tuple[UUID, ...]:
    """Return subject ids the student is enrolled in on a date."""
    enrolment_ids = [
        row.id
        for row in Enrolment.objects.filter(
            school_id=school_id, student_id=student_id, state="active"
        )
        if range_covers(
            from_date=row.from_date, to_date=row.to_date, effective_date=effective_date
        )
    ]
    subject_ids: list[UUID] = []
    for subject_row in SubjectEnrolment.objects.filter(
        school_id=school_id, enrolment_id__in=enrolment_ids
    ):
        if not range_covers(
            from_date=subject_row.from_date,
            to_date=subject_row.to_date,
            effective_date=effective_date,
        ):
            continue
        offering = SubjectOffering.objects.filter(id=subject_row.subject_offering_id).first()
        if offering is not None:
            subject_ids.append(offering.subject_id)
    return tuple(dict.fromkeys(subject_ids))
