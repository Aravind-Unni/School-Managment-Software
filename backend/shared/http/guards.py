"""Request-body guards for server-internal types.

ResourceGrant is minted server-side and must never arrive from a browser. A
module that forgot this would accept a forged grant, so the check lives in shared
middleware rather than in each serializer.
"""

from __future__ import annotations

from contracts.errors import FieldError, ValidationFailed

#: Keys that may never appear anywhere in an inbound request body.
SERVER_INTERNAL_KEYS: frozenset[str] = frozenset(
    {"resource_grant", "grant_id", "auth_level", "auth_time", "actor_id", "school_id"}
)


def assert_no_server_internal_keys(payload: object, path: str = "") -> None:
    """Recursively reject a body containing a server-internal key.

    Raises ValidationFailed (422) naming the offending path. Recurses into
    nested objects and arrays, because a grant hidden one level down is the
    interesting case.

    Does not handle: query parameters. Those are checked by the list view, which
    knows its own allowed parameter names.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            here = f"{path}.{key}" if path else str(key)
            if key in SERVER_INTERNAL_KEYS:
                raise ValidationFailed(
                    "error.server_internal_field_rejected",
                    field_errors=(FieldError(here, "error.field_not_accepted"),),
                )
            assert_no_server_internal_keys(value, here)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            assert_no_server_internal_keys(item, f"{path}[{index}]")
