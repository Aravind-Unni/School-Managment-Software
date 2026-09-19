"""Cookie policy for M01 sessions. One place, so it cannot drift per endpoint.

The session cookie is HttpOnly (JavaScript must never read it), SameSite (so a
cross-site form post carries no session) and Secure outside development. A separate
CSRF cookie is deliberately NOT HttpOnly, because the page must read it to echo it
back -- that is the double-submit pattern, and it is safe precisely because an
attacker on another origin cannot read it.
"""

from __future__ import annotations

import secrets

from django.conf import settings

SESSION_COOKIE_NAME = "school_session"
CSRF_COOKIE_NAME = "school_csrf"
CSRF_HEADER_NAME = "HTTP_X_CSRF_TOKEN"

#: Sessions are not remembered across browser restarts by default: a school device
#: is often shared, so a session cookie with no Max-Age is the safer default.
SESSION_MAX_AGE_SECONDS = 12 * 3600


def new_csrf_token() -> str:
    """Return a fresh CSRF token."""
    return secrets.token_urlsafe(24)


def cookie_kwargs(*, http_only: bool) -> dict[str, object]:
    """Return the shared cookie attributes for this deployment.

    ``Secure`` follows ``SESSION_COOKIE_SECURE``, which base settings leave False in
    development (where the stack is plain HTTP on loopback) and production sets True.
    Hardcoding Secure=True would make development silently session-less; hardcoding
    False would ship an insecure cookie.
    """
    return {
        "httponly": http_only,
        "secure": bool(getattr(settings, "SESSION_COOKIE_SECURE", False)),
        "samesite": "Lax",
        "path": "/",
        "max_age": SESSION_MAX_AGE_SECONDS,
    }


def set_session_cookie(response, token: str) -> str:
    """Attach the session and CSRF cookies. Returns the CSRF token.

    Called on every session creation and rotation, so a rotated session always
    carries a fresh CSRF token too.
    """
    response.set_cookie(SESSION_COOKIE_NAME, token, **cookie_kwargs(http_only=True))
    csrf_token = new_csrf_token()
    response.set_cookie(CSRF_COOKIE_NAME, csrf_token, **cookie_kwargs(http_only=False))
    return csrf_token


def clear_session_cookie(response) -> None:
    """Remove both cookies on logout."""
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
