"""M02's owned tables, split by responsibility.

Re-exported here so call sites import from ``modules.registry.models`` and do
not depend on which file a model happens to live in.
"""

from __future__ import annotations

from .configuration import (
    LANGUAGES,
    YEAR_STATES,
    AcademicYear,
    SchoolConfig,
    Section,
    Standard,
    Subject,
    Term,
)
from .enrolments import ENROLMENT_STATES, Enrolment, SubjectEnrolment
from .people import (
    DUPLICATE_REASONS,
    STUDENT_STATUSES,
    DuplicateReview,
    ExternalIdentity,
    Guardian,
    StaffProfile,
    Student,
    StudentPhoto,
)
from .relationships import VISIBILITY_CHOICES, GuardianLink, SubjectOffering, TeachingAssignment

__all__ = [
    "DUPLICATE_REASONS",
    "ENROLMENT_STATES",
    "LANGUAGES",
    "STUDENT_STATUSES",
    "VISIBILITY_CHOICES",
    "YEAR_STATES",
    "AcademicYear",
    "DuplicateReview",
    "Enrolment",
    "ExternalIdentity",
    "Guardian",
    "GuardianLink",
    "SchoolConfig",
    "Section",
    "StaffProfile",
    "Standard",
    "Student",
    "StudentPhoto",
    "Subject",
    "SubjectEnrolment",
    "SubjectOffering",
    "TeachingAssignment",
    "Term",
]
