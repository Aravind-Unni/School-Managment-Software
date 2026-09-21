"""Synthetic seed for the C02 integrated profile (MODULE_ID=ALL).

Creates the minimum school configuration and people/link/enrolment rows needed
for cross-module journeys. All identifiers come from ``shared.fixtures`` —
nothing here describes a real student.
"""

from __future__ import annotations

from datetime import date

from modules.registry import seeds as registry_seeds
from modules.registry.models import (
    AcademicYear,
    Enrolment,
    Guardian,
    GuardianLink,
    Section,
    StaffProfile,
    Standard,
    Student,
    Subject,
    SubjectEnrolment,
    SubjectOffering,
    TeachingAssignment,
)
from shared import fixtures


def integration() -> dict[str, int]:
    """Load the integrated synthetic cast into the shared database.

    Idempotent via fixed UUIDs from fixtures. Assumes migrations have applied.
    Does not handle: full multi-year history or production cutover data.
    """
    summary = registry_seeds.bootstrap(fixtures.SCHOOL_A)
    school_id = fixtures.SCHOOL_A
    now = registry_seeds.SEED_INSTANT

    year, _ = AcademicYear.objects.update_or_create(
        id=fixtures.fixture_uuid("integration.year"),
        defaults={
            "school_id": school_id,
            "name": "2026-2027",
            "start": date(2026, 6, 1),
            "end": date(2027, 3, 31),
            "state": "active",
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )
    standard, _ = Standard.objects.update_or_create(
        id=fixtures.fixture_uuid("integration.standard5"),
        defaults={
            "school_id": school_id,
            "number": 5,
            "archived": False,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )
    section, _ = Section.objects.update_or_create(
        id=fixtures.CLASS_C1,
        defaults={
            "school_id": school_id,
            "year": year,
            "standard": standard,
            "name": "A",
            "archived": False,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )
    subject, _ = Subject.objects.update_or_create(
        id=fixtures.SUBJECT_MATHS,
        defaults={
            "school_id": school_id,
            "code": "MATH",
            "display_name": "Mathematics",
            "archived": False,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )

    offering, _ = SubjectOffering.objects.update_or_create(
        id=fixtures.fixture_uuid("integration.offering.math"),
        defaults={
            "school_id": school_id,
            "year": year,
            "section": section,
            "subject": subject,
            "optional_group": None,
            "archived": False,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )

    for student_id, admission, name in (
        (fixtures.STUDENT_S1, "S1-2026", "Synthetic Student One"),
        (fixtures.STUDENT_S2, "S2-2026", "Synthetic Student Two"),
    ):
        Student.objects.update_or_create(
            id=student_id,
            defaults={
                "school_id": school_id,
                "admission_no": admission,
                "display_name": name,
                "date_of_birth": date(2015, 1, 15),
                "preferred_language": "en",
                "status": "active",
                "archived": False,
                "version": 1,
                "created_at": now,
                "updated_at": now,
            },
        )

    for guardian_id, label in (
        (fixtures.GUARDIAN_G1, "Synthetic Guardian One"),
        (fixtures.GUARDIAN_G2, "Synthetic Guardian Two"),
    ):
        Guardian.objects.update_or_create(
            id=guardian_id,
            defaults={
                "school_id": school_id,
                "display_name": label,
                "email": None,
                "phone": None,
                "archived": False,
                "version": 1,
                "created_at": now,
                "updated_at": now,
            },
        )

    StaffProfile.objects.update_or_create(
        id=fixtures.TEACHER_T1,
        defaults={
            "school_id": school_id,
            "display_name": "Synthetic Teacher One",
            "archived": False,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )

    GuardianLink.objects.update_or_create(
        id=fixtures.fixture_uuid("integration.link.g1.s1"),
        defaults={
            "school_id": school_id,
            "student_id": fixtures.STUDENT_S1,
            "guardian_id": fixtures.GUARDIAN_G1,
            "visibility": "academic",
            "from_date": date(2026, 6, 1),
            "to_date": None,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )
    GuardianLink.objects.update_or_create(
        id=fixtures.fixture_uuid("integration.link.g1.s2"),
        defaults={
            "school_id": school_id,
            "student_id": fixtures.STUDENT_S2,
            "guardian_id": fixtures.GUARDIAN_G1,
            "visibility": "academic",
            "from_date": date(2026, 6, 1),
            "to_date": None,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )

    TeachingAssignment.objects.update_or_create(
        id=fixtures.fixture_uuid("integration.assignment.t1"),
        defaults={
            "school_id": school_id,
            "staff_id": fixtures.TEACHER_T1,
            "section": section,
            "subject": subject,
            "from_date": date(2026, 6, 1),
            "to_date": None,
            "is_class_teacher": True,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        },
    )

    for student_id in (fixtures.STUDENT_S1, fixtures.STUDENT_S2):
        enrolment, _ = Enrolment.objects.update_or_create(
            id=fixtures.fixture_uuid(f"integration.enrolment.{student_id}"),
            defaults={
                "school_id": school_id,
                "student_id": student_id,
                "year": year,
                "section": section,
                "from_date": date(2026, 6, 1),
                "to_date": None,
                "previous_enrolment_id": None,
                "state": "active",
                "version": 1,
                "created_at": now,
                "updated_at": now,
            },
        )
        SubjectEnrolment.objects.update_or_create(
            id=fixtures.fixture_uuid(f"integration.subject_enrolment.{student_id}"),
            defaults={
                "school_id": school_id,
                "enrolment": enrolment,
                "subject_offering": offering,
                "from_date": date(2026, 6, 1),
                "to_date": None,
                "version": 1,
                "created_at": now,
                "updated_at": now,
            },
        )

    summary.update(
        {
            "students": 2,
            "guardians": 2,
            "guardian_links": 2,
            "staff": 1,
            "enrolments": 2,
            "teaching_assignments": 1,
        }
    )
    return summary


SCENARIOS = {"integration": integration}
