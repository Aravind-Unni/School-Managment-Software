"""Wire shapes for step 2-3 registry records."""

from __future__ import annotations

from ..models import (
    Enrolment,
    GuardianLink,
    SubjectEnrolment,
    SubjectOffering,
    TeachingAssignment,
)


def guardian_link_to_wire(row: GuardianLink) -> dict[str, object]:
    """Render a GuardianLink record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "student_id": str(row.student_id),
        "guardian_id": str(row.guardian_id),
        "visibility": row.visibility,
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat() if row.to_date else None,
    }


def teaching_assignment_to_wire(row: TeachingAssignment) -> dict[str, object]:
    """Render a TeachingAssignment record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "staff_id": str(row.staff_id),
        "section_id": str(row.section_id),
        "subject_id": str(row.subject_id),
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat() if row.to_date else None,
    }


def subject_offering_to_wire(row: SubjectOffering) -> dict[str, object]:
    """Render a SubjectOffering record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "year_id": str(row.year_id),
        "section_id": str(row.section_id),
        "subject_id": str(row.subject_id),
        "optional_group": row.optional_group,
        "archived": row.archived,
    }


def enrolment_to_wire(row: Enrolment) -> dict[str, object]:
    """Render an Enrolment record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "student_id": str(row.student_id),
        "year_id": str(row.year_id),
        "section_id": str(row.section_id),
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat() if row.to_date else None,
        "previous_enrolment_id": (
            str(row.previous_enrolment_id) if row.previous_enrolment_id else None
        ),
        "state": row.state,
    }


def subject_enrolment_to_wire(row: SubjectEnrolment) -> dict[str, object]:
    """Render a SubjectEnrolment record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "enrolment_id": str(row.enrolment_id),
        "subject_offering_id": str(row.subject_offering_id),
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat() if row.to_date else None,
    }
