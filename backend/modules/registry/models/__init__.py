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
from .people import (
    DUPLICATE_REASONS,
    STUDENT_STATUSES,
    DuplicateReview,
    ExternalIdentity,
    Guardian,
    StaffProfile,
    Student,
)

__all__ = [
    "DUPLICATE_REASONS",
    "LANGUAGES",
    "STUDENT_STATUSES",
    "YEAR_STATES",
    "AcademicYear",
    "DuplicateReview",
    "ExternalIdentity",
    "Guardian",
    "SchoolConfig",
    "Section",
    "StaffProfile",
    "Standard",
    "Student",
    "Subject",
    "Term",
]
