"""Immutable shared contracts for the school platform.

Everything importable here is frozen by ``contracts/manifest.json``. Changing a
name or a field in this package is a contract revision requiring owner review,
because every module and the generated TypeScript client depend on it.

RULES enforced by ``scripts/arch_check.py``:
  * No Django import anywhere in this package.
  * No business ORM model here, ever.
  * No module under ``backend/modules/`` may import another module.
"""

from .errors import (
    ActionDenied,
    ContractError,
    ErrorCode,
    ErrorEnvelope,
    FieldError,
    HTTP_STATUS_BY_CODE,
    ObjectInaccessible,
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
from .identity import AuthLevel, RequestContext
from .pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Page,
    clamp_page_size,
    decode_cursor,
    encode_cursor,
)
from .ports import (
    AccessPort,
    ClockPort,
    NotificationPort,
    ObjectStoragePort,
    PlatformPort,
    RegistryPort,
)
from .registration import (
    FrontendRoute,
    HealthCheck,
    ModuleRegistration,
    ScheduledJob,
)
from .scope import RelationshipFacts, Relationship, ScopeFacts
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
    "ActionDenied", "ContractError", "ErrorCode", "ErrorEnvelope", "FieldError",
    "HTTP_STATUS_BY_CODE", "ObjectInaccessible", "StaleAuth", "StateConflict",
    "Unauthenticated", "ValidationFailed", "VersionConflict",
    "EVENT_ENVELOPE_VERSION", "AuditRecord", "EventEnvelope",
    "EvidenceRef", "ResourceGrant",
    "AuthLevel", "RequestContext",
    "DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE", "Page", "clamp_page_size",
    "decode_cursor", "encode_cursor",
    "AccessPort", "ClockPort", "NotificationPort", "ObjectStoragePort",
    "PlatformPort", "RegistryPort",
    "FrontendRoute", "HealthCheck", "ModuleRegistration", "ScheduledJob",
    "RelationshipFacts", "Relationship", "ScopeFacts",
    "MARKS_DECIMAL_PLACES", "SCHOOL_TIMEZONE", "now_utc",
    "paise_from_rupee_string", "rupee_string_from_paise", "school_date",
    "validate_marks_string",
]
