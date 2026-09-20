"""Immutable shared contracts for the school platform.

Everything importable here is frozen by ``contracts/manifest.json``. Changing a
name or a field in this package is a contract revision requiring owner review,
because every module and the generated TypeScript client depend on it.

RULES enforced by ``scripts/arch_check.py``:
  * No Django import anywhere in this package.
  * No business ORM model here, ever.
  * No module under ``backend/modules/`` may import another module.
"""

from .decisions import (
    NOT_FOUND_REASONS,
    UNAUTHENTICATED_REASONS,
    Decision,
    ReasonCode,
)
from .errors import (
    HTTP_STATUS_BY_CODE,
    ActionDenied,
    ContractError,
    ErrorCode,
    ErrorEnvelope,
    FieldError,
    ObjectInaccessible,
    RateLimited,
    StaleAuth,
    StateConflict,
    Unauthenticated,
    ValidationFailed,
    VersionConflict,
)
from .events import (
    EVENT_ENVELOPE_VERSION,
    AuditRecord,
    EventEnvelope,
)
from .evidence import EvidenceRef, ResourceGrant
from .files import (
    ArtifactRef,
    FileDTO,
    FileEvidenceRef,
    ReadUrlDTO,
    UploadSession,
)
from .identity import AuthLevel, RequestContext
from .pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Page,
    clamp_page_size,
    decode_cursor,
    encode_cursor,
)
from .people import (
    RosterDTO,
    RosterEntry,
    StudentDTO,
    StudentStatus,
    TeachingAssignment,
)
from .performance import (
    DashboardDTO,
    InterventionDTO,
    InterventionPage,
    MetricDTO,
    SourceFreshnessDTO,
    WarningSummaryDTO,
)
from .ports import (
    AccessPort,
    AssessmentPort,
    AttendancePort,
    ClockPort,
    FilesPort,
    NotificationPort,
    ObjectStoragePort,
    PerformancePort,
    PlatformPort,
    RegistryPort,
    TimetablePort,
)
from .registration import (
    FrontendRoute,
    HealthCheck,
    ModuleRegistration,
    ScheduledJob,
    assert_no_registration_collisions,
)
from .scope import Relationship, RelationshipFacts, ScopeFacts
from .timetable import (
    AttendanceSummaryDTO,
    CalendarDayDTO,
    PeriodSessionDTO,
    TeachingAuthorityDTO,
)
from .values import (
    MARKS_DECIMAL_PLACES,
    SCHOOL_TIMEZONE,
    now_utc,
    paise_from_rupee_string,
    rupee_string_from_paise,
    school_date,
    validate_marks_string,
)

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "EVENT_ENVELOPE_VERSION",
    "HTTP_STATUS_BY_CODE",
    "MARKS_DECIMAL_PLACES",
    "MAX_PAGE_SIZE",
    "NOT_FOUND_REASONS",
    "SCHOOL_TIMEZONE",
    "UNAUTHENTICATED_REASONS",
    "AccessPort",
    "ActionDenied",
    "ArtifactRef",
    "AssessmentPort",
    "AttendancePort",
    "AttendanceSummaryDTO",
    "AuditRecord",
    "AuthLevel",
    "CalendarDayDTO",
    "ClockPort",
    "ContractError",
    "DashboardDTO",
    "Decision",
    "ErrorCode",
    "ErrorEnvelope",
    "EventEnvelope",
    "EvidenceRef",
    "FieldError",
    "FileDTO",
    "FileEvidenceRef",
    "FilesPort",
    "FrontendRoute",
    "HealthCheck",
    "InterventionDTO",
    "InterventionPage",
    "MetricDTO",
    "ModuleRegistration",
    "NotificationPort",
    "ObjectInaccessible",
    "ObjectStoragePort",
    "Page",
    "PerformancePort",
    "PeriodSessionDTO",
    "PlatformPort",
    "RateLimited",
    "ReadUrlDTO",
    "ReasonCode",
    "RegistryPort",
    "Relationship",
    "RelationshipFacts",
    "RequestContext",
    "ResourceGrant",
    "RosterDTO",
    "RosterEntry",
    "ScheduledJob",
    "ScopeFacts",
    "SourceFreshnessDTO",
    "StaleAuth",
    "StateConflict",
    "StudentDTO",
    "StudentStatus",
    "TeachingAssignment",
    "TeachingAuthorityDTO",
    "TimetablePort",
    "Unauthenticated",
    "UploadSession",
    "ValidationFailed",
    "VersionConflict",
    "WarningSummaryDTO",
    "assert_no_registration_collisions",
    "clamp_page_size",
    "decode_cursor",
    "encode_cursor",
    "now_utc",
    "paise_from_rupee_string",
    "rupee_string_from_paise",
    "school_date",
    "validate_marks_string",
]
