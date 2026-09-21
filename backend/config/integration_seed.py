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
    from modules.access import seeds as access_seeds

    access_summary = access_seeds.baseline()
    summary = registry_seeds.bootstrap(fixtures.SCHOOL_A)
    summary = {**access_summary, **summary}
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

    grant_summary = _ensure_integrated_module_grants()
    summary.update(
        {
            "students": 2,
            "guardians": 2,
            "guardian_links": 2,
            "staff": 1,
            "enrolments": 2,
            "teaching_assignments": 1,
            **grant_summary,
        }
    )
    return summary


#: Permission codes every integrated module registers (nav + AccessPort).
#: Auth.* login codes are not grantable; they are omitted here on purpose.
_MODULE_PERMISSION_CODES: tuple[str, ...] = (
    "registry.manage",
    "students.read",
    "students.update",
    "guardians.manage",
    "staff.assign",
    "year.close",
    "students.promote",
    "students.withdraw",
    "timetable.read",
    "timetable.read_section",
    "timetable.read_teacher",
    "timetable.read_student",
    "timetable.edit",
    "timetable.publish",
    "timetable.substitute",
    "attendance.read",
    "attendance.mark",
    "attendance.submit",
    "attendance.correct",
    "assessment.manage",
    "marks.edit",
    "marks.submit",
    "results.approve",
    "results.publish",
    "results.reopen",
    "evidence.view",
    "performance.read",
    "warnings.manage",
    "interventions.manage",
    "meetings.record",
    "observations.read_sensitive",
    "fees.configure",
    "fees.read",
    "fees.record_payment",
    "fees.concede",
    "fees.reverse_payment",
    "fees.refund",
    "transport.manage",
    "transport.read",
    "transport.bill",
    "library.catalogue.manage",
    "library.issue",
    "library.return",
    "library.renew",
    "library.read_overdues",
    "library.read_own",
    "alumni.review",
    "alumni.manage",
    "alumni.read",
    "alumni.export",
    "alumni.contact_self",
    "notices.create",
    "notices.publish",
    "messages.send",
    "messages.read_status",
    "sms.configure",
    "files.upload",
    "files.review_quality",
    "files.read",
    "files.retention.manage",
    "imports.validate",
    "imports.commit",
    "reports.read",
    "reports.export",
    "reportcards.generate",
    "platform.read_health",
    "jobs.read",
    "jobs.retry",
    "audit.read",
    "backups.manage",
)

#: Role label -> extra module actions for the integrated cast (synthetic only).
_ROLE_MODULE_ACTIONS: dict[str, tuple[str, ...]] = {
    "owner": _MODULE_PERMISSION_CODES,
    "administrator": _MODULE_PERMISSION_CODES,
    "teacher": (
        "students.read",
        "timetable.read",
        "timetable.read_section",
        "timetable.read_teacher",
        "timetable.edit",
        "timetable.substitute",
        "attendance.read",
        "attendance.mark",
        "attendance.submit",
        "attendance.correct",
        "assessment.manage",
        "marks.edit",
        "marks.submit",
        "evidence.view",
        "performance.read",
        "warnings.manage",
        "interventions.manage",
        "files.upload",
        "files.read",
        "library.read_own",
    ),
    "guardian": (
        "students.read",
        "timetable.read_student",
        "attendance.read",
        "evidence.view",
        "performance.read",
        "fees.read",
        "library.read_own",
        "files.read",
        "alumni.contact_self",
    ),
}


def _ensure_integrated_module_grants() -> dict[str, int]:
    """Register module permission codes and grant them to the synthetic roles.

    Assumes M01 baseline roles already exist. Does not remove existing M01 grants.
    Does not handle: production role design or school-specific custom roles.
    """
    from modules.access.models import Grant, Permission, Role
    from modules.access.scopes import ScopeType
    from modules.access.seeds import SEED_INSTANT, _id, _role_id

    for code in _MODULE_PERMISSION_CODES:
        Permission.objects.update_or_create(
            code=code,
            defaults={
                "description": f"Integrated grant surface for {code}",
                "requires_recent_two_factor": False,
            },
        )

    added = 0
    for role_label, actions in _ROLE_MODULE_ACTIONS.items():
        role = Role.objects.get(id=_role_id(role_label))
        for action in actions:
            _, created = Grant.objects.get_or_create(
                id=_id(f"integration.grant.{role_label}.{action}"),
                defaults={
                    "school_id": role.school_id,
                    "role": role,
                    "action": action,
                    "scope_type": ScopeType.SCHOOL.value,
                    "scope_id": None,
                    "valid_from": fixtures.TERM_START,
                    "valid_to": None,
                    "created_at": SEED_INSTANT,
                },
            )
            if created:
                added += 1
    return {"module_permissions": len(_MODULE_PERMISSION_CODES), "module_grants_added": added}


SCENARIOS = {"integration": integration}
