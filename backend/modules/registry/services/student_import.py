"""Admit many pupils at once from the office's admissions spreadsheet.

``preview`` reads the file and checks every row against the school: the class
must exist in the current academic year, and the admission number (or the
same name with the same birth date) must not already be on the roll. Nothing
is written. ``apply`` runs the same checks and, only when every row is clean,
admits every pupil in one transaction through the same services the
one-at-a-time Admit screen uses: the pupil, their parent (one parent record
per phone number, reused across siblings and existing records), the parent
link and the class placement, with compulsory subjects following from it.

Does not handle: parent logins (create those from Accounts), transfers of
pupils already on the roll, or partial imports (fix the file; nothing is half
done).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from django.db import transaction

from contracts.identity import RequestContext
from contracts.values import school_date

from ..models import AcademicYear, Guardian, Section, Student
from .duplicates import normalise_admission_no, normalise_display_name
from .student_import_parse import ParsedFile, ParsedRow, RowProblem, parse_file


@dataclass(frozen=True, slots=True)
class StudentImportService:
    """Preview and apply an admissions spreadsheet."""

    people: object
    links: object
    enrolments: object
    clock: object

    def preview(self, context: RequestContext, text: str) -> dict:
        """Check the file against the school and describe what would happen."""
        self.people._authorise(context, "students.update")
        parsed, year, sections = self._check(context, text)
        return self._summary(parsed, year, sections, applied=False)

    def apply(self, context: RequestContext, text: str) -> dict:
        """Admit every pupil in the file, or nobody when any row has a problem."""
        self.people._authorise(context, "students.update")
        parsed, year, sections = self._check(context, text)
        if parsed.problems or year is None:
            return self._summary(parsed, year, sections, applied=False)
        today = school_date(self.clock.now())
        from_date = max(today, year.start)
        guardians = _existing_guardians_by_phone(context.school_id)
        created_parents = 0
        with transaction.atomic():
            for row in parsed.rows:
                student = self.people.admit_student(
                    context,
                    admission_no=row.admission_no,
                    display_name=row.name,
                    date_of_birth=row.date_of_birth,
                    preferred_language=row.language,
                    external_ids=(),
                    acknowledgement=None,
                )
                if row.details:
                    Student.objects.filter(id=student.id).update(details=row.details)
                guardian_id = None
                if row.parent_phone and row.parent_phone in guardians:
                    guardian_id = guardians[row.parent_phone]
                elif row.parent_name or row.parent_phone:
                    guardian = self.people.create_guardian(
                        context,
                        display_name=row.parent_name or f"Parent of {row.name}",
                        email=row.parent_email or None,
                        phone=row.parent_phone or None,
                        external_ids=(),
                    )
                    created_parents += 1
                    guardian_id = guardian.id
                    if row.parent_phone:
                        guardians[row.parent_phone] = guardian.id
                if guardian_id is not None:
                    self.links.create_link(
                        context,
                        student_id=student.id,
                        guardian_id=guardian_id,
                        visibility="academic",
                        from_date=from_date,
                        to_date=None,
                    )
                self.enrolments.create_enrolment(
                    context,
                    student_id=student.id,
                    year_id=year.id,
                    section_id=sections[(row.standard, row.section_name)],
                    from_date=from_date,
                    to_date=None,
                )
        summary = self._summary(parsed, year, sections, applied=True)
        summary["parents_created"] = created_parents
        return summary

    # -- checks ---------------------------------------------------------------

    def _check(self, context: RequestContext, text: str):
        """Parse the file and add the problems only the school's records reveal."""
        parsed = parse_file(text)
        year = _current_year(context.school_id, school_date(self.clock.now()))
        sections: dict[tuple[int, str], object] = {}
        if year is None:
            parsed.problems.append(RowProblem(1, "file", "registry.import.no_year"))
            return parsed, None, sections
        for section in Section.objects.filter(
            school_id=context.school_id, year=year, archived=False
        ).select_related("standard"):
            sections[(section.standard.number, section.name.upper())] = section.id
        kept: list[ParsedRow] = []
        taken = _taken_admission_numbers(context.school_id, parsed.rows)
        same_person = _existing_name_and_birth(context.school_id, parsed.rows)
        for row in parsed.rows:
            problems = []
            if (row.standard, row.section_name) not in sections:
                problems.append(
                    RowProblem(
                        row.row, "class", "registry.import.unknown_class", row.class_text
                    )
                )
            if normalise_admission_no(row.admission_no) in taken:
                problems.append(
                    RowProblem(
                        row.row,
                        "admission_no",
                        "registry.import.already_admitted",
                        row.admission_no,
                    )
                )
            elif (normalise_display_name(row.name), row.date_of_birth) in same_person:
                problems.append(
                    RowProblem(row.row, "name", "registry.import.same_pupil", row.name)
                )
            parsed.problems.extend(problems)
            if not problems:
                kept.append(row)
        parsed.rows = kept
        return parsed, year, sections

    def _summary(self, parsed: ParsedFile, year, sections, *, applied: bool) -> dict:
        """Describe the file: ready rows per class, and every problem in row order."""
        labels = {key: f"Std {key[0]} – {key[1]}" for key in sections}  # noqa: RUF001 -- label typography
        per_class = Counter(labels[(row.standard, row.section_name)] for row in parsed.rows)
        phones = {row.parent_phone for row in parsed.rows if row.parent_phone}
        return {
            "applied": applied and not parsed.problems,
            "year": year.name if year is not None else None,
            "ready": len(parsed.rows),
            "per_class": dict(sorted(per_class.items())),
            "parents_with_phone": len(phones),
            "problems": [
                problem.to_wire()
                for problem in sorted(parsed.problems, key=lambda item: (item.row, item.column))
            ],
        }


def _current_year(school_id, today: date):
    """Return the academic year containing today, else the latest one."""
    years = AcademicYear.objects.filter(school_id=school_id)
    return (
        years.filter(start__lte=today, end__gte=today).first()
        or years.order_by("-start").first()
    )


def _taken_admission_numbers(school_id, rows: list[ParsedRow]) -> set[str]:
    """Admission numbers from the file that are already on the school's roll."""
    wanted = {normalise_admission_no(row.admission_no) for row in rows}
    return set(
        Student.objects.filter(school_id=school_id, admission_no__in=wanted).values_list(
            "admission_no", flat=True
        )
    )


def _existing_name_and_birth(school_id, rows: list[ParsedRow]) -> set[tuple[str, date]]:
    """(name, birth date) pairs from the file that match a pupil already admitted."""
    births = {row.date_of_birth for row in rows if row.date_of_birth is not None}
    if not births:
        return set()
    return {
        (normalise_display_name(name), born)
        for name, born in Student.objects.filter(
            school_id=school_id, date_of_birth__in=births
        ).values_list("display_name", "date_of_birth")
    }


def _existing_guardians_by_phone(school_id) -> dict[str, object]:
    """Map phone number to an existing parent record, so siblings share a parent."""
    return {
        phone: guardian_id
        for guardian_id, phone in Guardian.objects.filter(school_id=school_id, archived=False)
        .exclude(phone__isnull=True)
        .values_list("id", "phone")
        if phone
    }
