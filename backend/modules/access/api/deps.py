"""Service assembly and request helpers for M01's views.

Views never build a service themselves, so the wiring -- which ports, which clock --
exists once and a test can replace it wholesale.
"""

from __future__ import annotations

from django.conf import settings

from contracts.errors import Unauthenticated
from contracts.identity import RequestContext

from ..services.authorize import AccessService
from ..services.platform_facade import PlatformFacade


def clock():
    """Return the injected clock.

    From settings, so a test freezes time by overriding one setting rather than
    patching a module global.
    """
    return settings.SCHOOL_CLOCK


def ports():
    """Return the PortRegistry the profile bound.

    Read from the process-level holder, not from settings: an attribute stashed on
    settings disappears when an override_settings block pops, which made a view fail
    mid-test with AttributeError.
    """
    from shared.ports import runtime

    return runtime.get_registry()


def access_service() -> AccessService:
    """Return M01's real Access service."""
    return AccessService(clock=clock())


def platform() -> PlatformFacade:
    """Return the Platform facade with M01's specified signatures."""
    return PlatformFacade(platform=ports().resolve("platform"), clock=clock())


def registry():
    """Return the Registry port.

    A deterministic fake in standalone mode. M01 uses it only to resolve
    relationships; it never reads Registry's ORM.
    """
    return ports().resolve("registry")


def require_session(request):
    """Return the live Session for a request, or raise Unauthenticated.

    Used by endpoints that need a session but no particular permission -- logout,
    reading one's own sessions. A revoked or absent session is a 401.
    """
    session = getattr(request, "school_session", None)
    if session is None:
        raise Unauthenticated("error.unauthenticated")
    return session


def require_context(request) -> RequestContext:
    """Return the trusted RequestContext, or raise Unauthenticated."""
    context = getattr(request, "school_context", None)
    if context is None:
        raise Unauthenticated("error.unauthenticated")
    return context


def remote_addr(request) -> str:
    """Return the client address for throttling.

    Reads REMOTE_ADDR only. X-Forwarded-For is deliberately ignored: it is
    client-controlled, so trusting it would let an attacker rotate the header and
    defeat per-address throttling entirely. A deployment behind a proxy must
    configure the proxy to set REMOTE_ADDR.
    """
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def user_agent(request) -> str:
    """Return the raw User-Agent, used only to derive a coarse family."""
    return request.META.get("HTTP_USER_AGENT", "")
