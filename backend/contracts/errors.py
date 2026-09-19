"""Stable error taxonomy shared by every module's API, services and workers.

The wire shape is fixed by the foundation contract and MUST NOT be extended
per module: ``{code, message_key, field_errors, request_id}``.

Does not handle: HTTP rendering (see backend/shared/http/error_handler.py),
translation of ``message_key`` into English/Malayalam text (a frontend concern),
or logging.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


class ErrorCode(enum.StrEnum):
    """Closed set of machine-readable error codes and their HTTP statuses.

    Adding a member is a contract revision: it requires a new
    ``contracts/manifest.json`` revision reviewed by the contract owner.
    """

    UNAUTHENTICATED = "unauthenticated"
    STALE_AUTH = "stale_auth"
    ACTION_DENIED = "action_denied"
    OBJECT_INACCESSIBLE = "object_inaccessible"
    VERSION_CONFLICT = "version_conflict"
    STATE_CONFLICT = "state_conflict"
    VALIDATION_FAILED = "validation_failed"


#: Authoritative code -> HTTP status mapping. 401/403/404/409/422 only.
#: ``STALE_AUTH`` is 401 because the remedy is to re-assert 2FA, not to ask for
#: a different permission.
HTTP_STATUS_BY_CODE: Mapping[ErrorCode, int] = MappingProxyType(
    {
        ErrorCode.UNAUTHENTICATED: 401,
        ErrorCode.STALE_AUTH: 401,
        ErrorCode.ACTION_DENIED: 403,
        ErrorCode.OBJECT_INACCESSIBLE: 404,
        ErrorCode.VERSION_CONFLICT: 409,
        ErrorCode.STATE_CONFLICT: 409,
        ErrorCode.VALIDATION_FAILED: 422,
    }
)


@dataclass(frozen=True, slots=True)
class FieldError:
    """One field-scoped validation problem.

    ``field`` is a dotted path into the request body using the wire field names
    (``guardian.contact_number``), never an ORM attribute path.
    """

    field: str
    message_key: str


class ContractError(Exception):
    """Base class for every error that crosses a module boundary.

    Carries no HTTP knowledge and no user-facing prose: ``message_key`` is a
    stable lookup key that the frontend renders in English or Malayalam.

    Does not handle: request_id assignment. The HTTP layer stamps request_id
    from the RequestContext at render time, because services raising these
    errors must not need to know the transport.
    """

    code: ErrorCode = ErrorCode.VALIDATION_FAILED

    def __init__(
        self,
        message_key: str,
        *,
        field_errors: tuple[FieldError, ...] = (),
    ) -> None:
        """Record the stable message key and any field-scoped problems."""
        super().__init__(message_key)
        self.message_key = message_key
        self.field_errors = field_errors

    @property
    def http_status(self) -> int:
        """Return the HTTP status this error renders as."""
        return HTTP_STATUS_BY_CODE[self.code]


class Unauthenticated(ContractError):
    """No usable session. Renders 401."""

    code = ErrorCode.UNAUTHENTICATED


class StaleAuth(ContractError):
    """Session is authentic but its 2FA assertion is too old. Renders 401.

    Raised by Access when ``auth_time`` is older than the action's freshness
    requirement. The fake Access adapter simulates this deliberately.
    """

    code = ErrorCode.STALE_AUTH


class ActionDenied(ContractError):
    """Actor may not perform this action in this scope. Renders 403.

    Used when the actor is permitted to know the object exists.
    """

    code = ErrorCode.ACTION_DENIED


class ObjectInaccessible(ContractError):
    """Object does not exist, or exists and must not be revealed. Renders 404.

    Deliberately conflates "absent" and "not yours" so that cross-school and
    cross-guardian probing cannot distinguish them.
    """

    code = ErrorCode.OBJECT_INACCESSIBLE


class VersionConflict(ContractError):
    """``expected_version`` did not match the stored aggregate. Renders 409."""

    code = ErrorCode.VERSION_CONFLICT

    def __init__(
        self,
        message_key: str = "error.version_conflict",
        *,
        expected_version: int | None = None,
        actual_version: int | None = None,
    ) -> None:
        """Record both versions so the client can show a useful conflict."""
        super().__init__(message_key)
        self.expected_version = expected_version
        self.actual_version = actual_version


class StateConflict(ContractError):
    """Aggregate is in a state that forbids this transition. Renders 409."""

    code = ErrorCode.STATE_CONFLICT


class ValidationFailed(ContractError):
    """Business validation rejected the input. Renders 422."""

    code = ErrorCode.VALIDATION_FAILED


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    """The exact JSON body returned for every non-2xx API response.

    Does not handle: HTTP status. Status is derived from ``code`` via
    HTTP_STATUS_BY_CODE by the renderer.
    """

    code: ErrorCode
    message_key: str
    request_id: str
    field_errors: tuple[FieldError, ...] = field(default=())

    def to_wire(self) -> dict[str, object]:
        """Serialise to the frozen wire shape.

        ``field_errors`` is always present as a list, empty when there are
        none, so clients never branch on key absence.
        """
        return {
            "code": str(self.code),
            "message_key": self.message_key,
            "request_id": self.request_id,
            "field_errors": [
                {"field": fe.field, "message_key": fe.message_key} for fe in self.field_errors
            ],
        }
