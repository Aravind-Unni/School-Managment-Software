"""Row-to-wire rendering for M02's browser responses.

Kept out of the views so the shape a consumer sees is defined once, next to the
frozen schema it mirrors, rather than assembled inline at each call site where
a field is easy to forget.
"""

from __future__ import annotations

from ..models import (
    AcademicYear,
    Guardian,
    SchoolConfig,
    Section,
    StaffProfile,
    Standard,
    Student,
    Subject,
    Term,
)


def school_config_to_wire(row: SchoolConfig) -> dict[str, object]:
    """Render the SchoolConfig record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "display_name": row.display_name,
        "board": row.board,
        "default_language": row.default_language,
        "settings": dict(row.settings or {}),
    }


def academic_year_to_wire(row: AcademicYear) -> dict[str, object]:
    """Render the AcademicYear record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "name": row.name,
        "start": row.start.isoformat(),
        "end": row.end.isoformat(),
        "state": row.state,
    }


def term_to_wire(row: Term) -> dict[str, object]:
    """Render the Term record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "year_id": str(row.year_id),
        "name": row.name,
        "start": row.start.isoformat(),
        "end": row.end.isoformat(),
        "archived": row.archived,
    }


def standard_to_wire(row: Standard) -> dict[str, object]:
    """Render the Standard record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "number": row.number,
        "archived": row.archived,
    }


def section_to_wire(row: Section) -> dict[str, object]:
    """Render the Section record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "year_id": str(row.year_id),
        "standard_id": str(row.standard_id),
        "name": row.name,
        "archived": row.archived,
    }


def subject_to_wire(row: Subject) -> dict[str, object]:
    """Render the Subject record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "code": row.code,
        "display_name": row.display_name,
        "archived": row.archived,
    }


def student_record_to_wire(
    row: Student, external_ids: list[dict[str, str]]
) -> dict[str, object]:
    """Render the versioned browser StudentRecord.

    Deliberately NOT the same shape as contracts.people.StudentDTO: that one is
    what other modules consume and carries no version or profile. Keeping them
    separate is what lets this record grow without breaking a consumer.
    """
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "admission_no": row.admission_no,
        "display_name": row.display_name,
        "status": row.status,
        "profile": {
            "date_of_birth": row.date_of_birth.isoformat() if row.date_of_birth else None,
            "preferred_language": row.preferred_language,
        },
        "external_ids": external_ids,
        "archived": row.archived,
    }


def guardian_to_wire(row: Guardian, external_ids: list[dict[str, str]]) -> dict[str, object]:
    """Render the Guardian record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "display_name": row.display_name,
        "email": row.email,
        "phone": row.phone,
        "external_ids": external_ids,
        "archived": row.archived,
    }


def staff_to_wire(row: StaffProfile, external_ids: list[dict[str, str]]) -> dict[str, object]:
    """Render the Staff record."""
    return {
        "id": str(row.id),
        "school_id": str(row.school_id),
        "version": row.version,
        "display_name": row.display_name,
        "external_ids": external_ids,
        "archived": row.archived,
    }
