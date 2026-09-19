"""Renders every exception as the frozen error envelope.

Installed as DRF's EXCEPTION_HANDLER. Guarantees that no endpoint in any module
can invent its own error shape, and that an unexpected exception never leaks a
traceback or an ORM message to a browser.

Does not handle: logging. The middleware logs with the request id; this function
only shapes the response.
"""

from __future__ import annotations

import logging

from rest_framework.response import Response

from contracts.errors import ContractError, ErrorCode, ErrorEnvelope, FieldError

from .context import SpoofedIdentityHeader

logger = logging.getLogger("school.errors")


def _request_id(context: dict | None) -> str:
    """Extract the request id from DRF's handler context.

    Falls back to ``"unknown"`` rather than raising: an error response must
    never itself fail.
    """
    request = (context or {}).get("request")
    ctx = getattr(request, "school_context", None)
    if ctx is not None:
        return ctx.request_id
    return getattr(request, "school_request_id", None) or "unknown"


def exception_handler(exc: Exception, context: dict | None = None) -> Response | None:
    """Convert an exception into the stable envelope.

    Handled explicitly:
      * ContractError subclasses -> their declared code and HTTP status
      * SpoofedIdentityHeader    -> 400, naming the offending header
      * DRF ValidationError      -> 422 with field_errors
    Anything else returns None so Django's own 500 handling applies; we do not
    dress an unknown crash up as a business error.
    """
    request_id = _request_id(context)

    if isinstance(exc, SpoofedIdentityHeader):
        envelope = ErrorEnvelope(
            code=ErrorCode.VALIDATION_FAILED,
            message_key="error.client_asserted_identity",
            request_id=request_id,
            field_errors=(FieldError(exc.header, "error.header_not_accepted"),),
        )
        logger.warning(
            "rejected client-asserted identity header",
            extra={"request_id": request_id, "header": exc.header},
        )
        return Response(envelope.to_wire(), status=400)

    if isinstance(exc, ContractError):
        envelope = ErrorEnvelope(
            code=exc.code,
            message_key=exc.message_key,
            request_id=request_id,
            field_errors=exc.field_errors,
        )
        response = Response(envelope.to_wire(), status=exc.http_status)
        retry_after = getattr(exc, "retry_after_seconds", None)
        if retry_after is not None:
            # A throttled client must be told how long to wait, or it will
            # hammer and make the throttle worse.
            response["Retry-After"] = str(int(retry_after))
        return response

    from rest_framework.exceptions import ValidationError as DRFValidationError

    if isinstance(exc, DRFValidationError):
        field_errors = tuple(
            FieldError(field=str(field), message_key=str(message))
            for field, messages in _flatten_drf_detail(exc.detail).items()
            for message in messages
        )
        envelope = ErrorEnvelope(
            code=ErrorCode.VALIDATION_FAILED,
            message_key="error.validation_failed",
            request_id=request_id,
            field_errors=field_errors,
        )
        return Response(envelope.to_wire(), status=422)

    return None


def _flatten_drf_detail(detail: object, prefix: str = "") -> dict[str, list[str]]:
    """Flatten DRF's nested error detail into dotted field paths.

    Does not handle: non-string leaf values other than by str() coercion, which
    is sufficient because message keys are always strings.
    """
    flattened: dict[str, list[str]] = {}
    if isinstance(detail, dict):
        for key, value in detail.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_drf_detail(value, path))
    elif isinstance(detail, list):
        if all(not isinstance(item, (dict, list)) for item in detail):
            flattened[prefix or "non_field"] = [str(item) for item in detail]
        else:
            for index, item in enumerate(detail):
                flattened.update(_flatten_drf_detail(item, f"{prefix}[{index}]"))
    else:
        flattened[prefix or "non_field"] = [str(detail)]
    return flattened
