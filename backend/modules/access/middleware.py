"""M01's authentication middleware. Runs BEFORE the shared context middleware.

Resolves the session cookie into a trusted RequestContext. The school comes from
the SESSION ROW, never from the request, which is what makes "never trust a client
school claim" structural rather than a convention.

Also enforces CSRF on unsafe methods using double-submit: the page echoes the
readable CSRF cookie in a header, and a cross-origin attacker cannot read that
cookie to forge the header.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import JsonResponse

from contracts.errors import ContractError, ValidationFailed
from contracts.values import now_utc

from .cookies import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from .services import sessions

logger = logging.getLogger("school.access")

#: Methods that cannot change state, so they need no CSRF token.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

#: Paths that must work with no session at all. Kept in sync with the module's
#: declared ``public_paths`` by tests/modules/M01.
PUBLIC_SUFFIXES = (
    "auth/login",
    "auth/2fa/verify",
    "auth/2fa/recover",
    "auth/2fa/enroll",
    "auth/2fa/confirm",
)


class AccessSessionMiddleware:
    """Attaches ``request.school_context`` from M01's session cookie."""

    def __init__(self, get_response) -> None:
        """Store the next handler."""
        self._get_response = get_response

    def __call__(self, request):
        """Resolve the session, enforce CSRF, then delegate.

        A missing or invalid session is NOT an error here: the shared middleware
        (for a protected path) or the view (for a public one) decides. This
        middleware only reports what it found, which keeps the authorisation
        decision in one place.
        """
        request.school_session = None
        token = request.COOKIES.get(SESSION_COOKIE_NAME, "")

        if token:
            session = sessions.resolve_session(token, instant=now_utc())
            if session is not None:
                request.school_session = session
                request.school_request_id = (
                    getattr(request, "school_request_id", None) or _new_request_id()
                )
                request.school_context = sessions.context_from_session(
                    session, request_id=request.school_request_id
                )

        if request.method not in SAFE_METHODS and _needs_csrf(request):
            try:
                _assert_csrf(request)
            except ContractError as exc:
                return _envelope(request, exc)

        return self._get_response(request)


def _new_request_id() -> str:
    """Return a fresh request id."""
    from shared.http.context import new_request_id

    return new_request_id()


def _needs_csrf(request) -> bool:
    """Return whether this request must carry a CSRF token.

    Only cookie-authenticated requests need it. Login itself does not: there is no
    session to ride, so there is nothing for an attacker to forge with.
    """
    if not request.COOKIES.get(SESSION_COOKIE_NAME):
        return False
    return not request.path.endswith(PUBLIC_SUFFIXES)


def _assert_csrf(request) -> None:
    """Raise ValidationFailed unless the header matches the cookie.

    Compared with ``secrets.compare_digest`` so a partial match cannot be found by
    timing. A missing cookie or header is a failure, never a skip.
    """
    import secrets

    cookie = request.COOKIES.get(CSRF_COOKIE_NAME, "")
    header = request.META.get(CSRF_HEADER_NAME, "")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        logger.warning(
            "csrf check failed",
            extra={
                "path": request.path,
                "request_id": getattr(request, "school_request_id", ""),
            },
        )
        raise ValidationFailed("error.csrf_failed")


def _envelope(request, exc: ContractError) -> JsonResponse:
    """Render a ContractError as the frozen envelope."""
    return JsonResponse(
        {
            "code": str(exc.code),
            "message_key": exc.message_key,
            "request_id": getattr(request, "school_request_id", "unknown"),
            "field_errors": [
                {"field": fe.field, "message_key": fe.message_key} for fe in exc.field_errors
            ],
        },
        status=exc.http_status,
    )


#: Re-exported so the profile can reference the dotted path without importing.
MIDDLEWARE_PATH = "modules.access.middleware.AccessSessionMiddleware"

_ = settings  # imported for symmetry with other modules; not read at import time
