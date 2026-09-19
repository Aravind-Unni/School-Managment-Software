"""DTOs returned by Registry (M02), consumed by other modules.

Added for M01, which needs more from Registry than B00 froze. These are the
shapes the future real provider must return, and the shapes the deterministic
fake must validate against -- a fake that answered a different shape would let a
consumer ship code that breaks at integration.

Does not handle: persistence. Registry owns the ORM; nothing here touches it.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


class StudentStatus(enum.StrEnum):
    """Enrolment state of a student, as Registry reports it."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSFERRED = "transferred"
    GRADUATED = "graduated"


@dataclass(frozen=True, slots=True)
class StudentDTO:
    """One student, as seen by a consuming module.

    Carries no guardian list and no contact details: a consumer that needs a
    relationship asks ``get_relationships`` and gets an answer, not the data to
    derive one itself.
    """

    id: UUID
    school_id: UUID
    admission_no: str
    display_name: str
    status: StudentStatus

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted shape."""
        return {
            "id": str(self.id),
            "school_id": str(self.school_id),
            "admission_no": self.admission_no,
            "display_name": self.display_name,
            "status": str(self.status),
        }


@dataclass(frozen=True, slots=True)
class RosterEntry:
    """One pupil on a roster."""

    student_id: UUID
    enrolment_id: UUID
    display_name: str

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted shape."""
        return {
            "student_id": str(self.student_id),
            "enrolment_id": str(self.enrolment_id),
            "display_name": self.display_name,
        }


@dataclass(frozen=True, slots=True)
class RosterDTO:
    """The pupils in a section on one date, optionally filtered by subject.

    When ``subject_id`` is set, ``students`` contains ONLY pupils enrolled in that
    subject offering on that date. That filtered roster is the one a timetable
    period must use; using the unfiltered section roster would mark attendance for
    pupils who do not take the subject.

    ``version`` is the roster's integer version, so a consumer writing against it
    can send ``expected_version`` and get a 409 rather than silently overwriting.
    """

    section_id: UUID
    date: date
    version: int
    students: tuple[RosterEntry, ...] = field(default_factory=tuple)
    subject_id: UUID | None = None

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted shape."""
        return {
            "section_id": str(self.section_id),
            "date": self.date.isoformat(),
            "subject_id": str(self.subject_id) if self.subject_id else None,
            "version": self.version,
            "students": [entry.to_wire() for entry in self.students],
        }


@dataclass(frozen=True, slots=True)
class TeachingAssignment:
    """One staff member's dated assignment to a section and subject.

    ``to_date`` None means open-ended. A consumer must compare against the
    school-local effective date, not UTC now.
    """

    section_id: UUID
    subject_id: UUID
    from_date: date
    to_date: date | None = None

    def covers(self, effective_date: date) -> bool:
        """Return whether this assignment is in force on a date.

        ``from_date`` is inclusive and ``to_date`` is inclusive, matching how a
        school states a posting ("from 1 June to 31 March").
        """
        if effective_date < self.from_date:
            return False
        return self.to_date is None or effective_date <= self.to_date

    def to_wire(self) -> dict[str, object]:
        """Serialise to the contracted shape."""
        return {
            "section_id": str(self.section_id),
            "subject_id": str(self.subject_id),
            "from_date": self.from_date.isoformat(),
            "to_date": self.to_date.isoformat() if self.to_date else None,
        }
