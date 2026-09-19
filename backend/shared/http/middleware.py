"""Middleware attaching the trusted context and guarding request bodies.

Order matters: this must run before any view so that ``request.school_context``
is available, and before body parsing conveniences so that a forged grant never
reaches a serializer.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import JsonResponse

from contracts.errors import ContractError

from .context import (
    DevPersona,
    SpoofedIdentityHeader,
    new_request_id,
    resolve_request_context,
)
from .guards import assert_no_server_internal_keys

logger = logging.getLogger("school.request")

#: Paths that must work without an identity: liveness, readiness and schema.
UNAUTHENTICATED_PATHS: tuple[str, ...] = ("/healthz", "/readyz", "/api/schema")


class RequestContextMiddleware:
    """Attaches ``request.school_context`` and rejects spoofed identity.

    Unauthenticated paths still get a request id so their logs correlate, but no
    context, because they have no actor.
    """

    def __init__(self, get_response) -> None:
        """Store the next handler in the chain."""
        self._get_response = get_response

    def __call__(self, request):
        """Resolve context, guard the body, then delegate.

        Returns the stable error envelope directly for identity and guard
        failures, because these happen before DRF's handler is in play.
        """
        request.school_request_id = (
            getattr(request, "school_request_id", None) or new_request_id()
        )

        if request.path.startswith(UNAUTHENTICATED_PATHS):
            return self._get_response(request)

        try:
            self._guard_body(request)
            request.school_context = resolve_request_context(
                meta=request.META,
                app_env=settings.APP_ENV,
                dev_persona_mode=settings.DEV_PERSONA_MODE,
                persona=self._persona(),
                clock=settings.SCHOOL_CLOCK,
            )
        except SpoofedIdentityHeader as exc:
            logger.warning(
                "rejected client-asserted identity header",
                extra={"request_id": request.school_request_id, "header": exc.header},
            )
            return self._envelope_response(
                request,
                code="validation_failed",
                message_key="error.client_asserted_identity",
                status=400,
                field_errors=[
                    {"field": exc.header, "message_key": "error.header_not_accepted"}
                ],
            )
        except ContractError as exc:
            return self._envelope_response(
                request,
                code=str(exc.code),
                message_key=exc.message_key,
                status=exc.http_status,
                field_errors=[
                    {"field": fe.field, "message_key": fe.message_key}
                    for fe in exc.field_errors
                ],
            )

        return self._get_response(request)

    def _guard_body(self, request) -> None:
        """Reject server-internal keys in a JSON body.

        Non-JSON and empty bodies are left alone; a malformed JSON body is left
        to the view's parser so the error message stays specific.
        """
        if request.method in ("GET", "HEAD", "OPTIONS", "DELETE"):
            return
        if "application/json" not in request.META.get("CONTENT_TYPE", ""):
            return
        if not request.body:
            return
        try:
            payload = json.loads(request.body)
        except ValueError:
            return
        assert_no_server_internal_keys(payload)

    def _persona(self) -> DevPersona | None:
        """Return the configured development persona, if any.

        Reads settings rather than the request, which is the whole point: the
        persona is a server-side decision.
        """
        return getattr(settings, "DEV_PERSONA", None)

    def _envelope_response(
        self,
        request,
        *,
        code: str,
        message_key: str,
        status: int,
        field_errors: list[dict[str, str]],
    ) -> JsonResponse:
        """Render the frozen error envelope as a JsonResponse."""
        return JsonResponse(
            {
                "code": code,
                "message_key": message_key,
                "request_id": request.school_request_id,
                "field_errors": field_errors,
            },
            status=status,
        )
