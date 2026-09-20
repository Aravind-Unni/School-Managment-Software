"""Derives the trusted RequestContext for each HTTP request.

The single rule this module exists to enforce: the school, the actor and the
authorisation level are decided SERVER-SIDE. A client may not assert them, and a
request that tries is rejected outright rather than ignored, because silently
dropping a spoofed header hides an attack and a bug equally well.

Development personas are available only when all three hold:
  * ``DEV_PERSONA_MODE=fixed``
  * ``APP_ENV`` is not ``production``
  * the peer is loopback, or is inside a network the profile explicitly trusts
    -- which only the containerised development stack configures, and which is
    explained in full on ``is_trusted_persona_peer``

Does not handle: real login, sessions, TOTP or recovery. M01 replaces the
persona path with real authentication; until then modules leave real
authentication integration explicitly pending.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from contracts.errors import Unauthenticated
from contracts.identity import AuthLevel, RequestContext

#: Headers a client might use to assert identity. Any of these present on an
#: inbound request is a hard 400 -- see SpoofedIdentityHeader.
FORBIDDEN_CLIENT_HEADERS: frozenset[str] = frozenset(
    {
        "HTTP_X_SCHOOL_ID",
        "HTTP_X_SCHOOL",
        "HTTP_X_ACTOR_ID",
        "HTTP_X_USER_ID",
        "HTTP_X_ROLE",
        "HTTP_X_ROLES",
        "HTTP_X_RELATIONSHIP",
        "HTTP_X_AUTH_LEVEL",
        "HTTP_X_PERSONA",
        "HTTP_X_ON_BEHALF_OF",
    }
)

#: Loopback peers permitted to use a development persona.
LOOPBACK_ADDRESSES: frozenset[str] = frozenset({"127.0.0.1", "::1", "localhost"})


class SpoofedIdentityHeader(Exception):
    """Raised when a request carries a client-asserted identity header."""

    def __init__(self, header: str) -> None:
        """Record which header was rejected, for the 400 body and the log."""
        super().__init__(header)
        self.header = header


@dataclass(frozen=True, slots=True)
class DevPersona:
    """A fixed synthetic persona, chosen by server configuration only.

    ``actor_id`` and ``school_id`` come from ``shared.fixtures``; the browser has
    no way to select or change them.
    """

    actor_id: uuid.UUID
    school_id: uuid.UUID
    auth_level: AuthLevel = AuthLevel.TWO_FACTOR


def new_request_id() -> str:
    """Return a fresh request id.

    Used when the caller supplied none. Correlation ids from a trusted upstream
    proxy are not honoured here because there is no trusted proxy in the
    development profiles this foundation ships.
    """
    return uuid.uuid4().hex


def assert_no_client_identity_headers(meta: dict[str, object]) -> None:
    """Raise SpoofedIdentityHeader if the request asserts its own identity.

    ``meta`` is Django's ``request.META``. Rejecting rather than stripping means
    a misconfigured client fails loudly in development instead of silently
    running as the wrong persona.
    """
    for header in FORBIDDEN_CLIENT_HEADERS:
        if header in meta:
            raise SpoofedIdentityHeader(header)


def is_loopback(remote_addr: str | None) -> bool:
    """Return whether the peer address is loopback.

    Assumes no reverse proxy is rewriting REMOTE_ADDR; the development profiles
    bind directly, and production never takes this path at all.
    """
    return (remote_addr or "") in LOOPBACK_ADDRESSES


def is_trusted_persona_peer(
    remote_addr: str | None, *, trusted_networks: tuple[str, ...] = ()
) -> bool:
    """Return whether a peer may use the fixed development persona.

    Loopback always qualifies. ``trusted_networks`` extends that, and is EMPTY
    unless a profile deliberately configures it.

    Why it exists: in the containerised development stack the API's port is
    published to 127.0.0.1 only, so the persona is unreachable from any network
    -- but Docker NATs the connection, so the peer the container SEES is the
    bridge gateway (172.x.0.1), never 127.0.0.1. The loopback test therefore
    refused every browser request with 401, which is why no module's browser
    suite had ever passed against a real stack.

    The property being preserved is "the persona is reachable only from the
    developer's own machine", and the port publication is what enforces it. This
    function widens WHICH peer addresses count, for a profile that has said so;
    it does not widen who can reach the port.

    Does not handle: production. The caller refuses the persona branch outright
    when APP_ENV is production, and PortRegistry.assert_production_safe refuses
    to start at all with DEV_PERSONA_MODE set. Both still apply, and a
    production profile must never populate ``trusted_networks``.
    """
    if is_loopback(remote_addr):
        return True
    if not remote_addr or not trusted_networks:
        return False
    import ipaddress

    try:
        peer = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    for network in trusted_networks:
        try:
            if peer in ipaddress.ip_network(network, strict=False):
                return True
        except ValueError:
            continue
    return False


def build_dev_context(
    persona: DevPersona,
    *,
    clock,
    request_id: str | None = None,
) -> RequestContext:
    """Build a RequestContext for the configured development persona.

    ``clock`` is a ClockPort, so ``auth_time`` is controllable in tests. The
    persona is always treated as having just asserted 2FA, because the fake
    Access adapter is what exercises the stale path deliberately.
    """
    return RequestContext(
        actor_id=persona.actor_id,
        school_id=persona.school_id,
        request_id=request_id or new_request_id(),
        auth_level=persona.auth_level,
        auth_time=clock.now(),
    )


def resolve_request_context(
    *,
    meta: dict[str, object],
    app_env: str,
    dev_persona_mode: str,
    persona: DevPersona | None,
    clock,
    trusted_persona_networks: tuple[str, ...] = (),
) -> RequestContext:
    """Return the trusted context for a request, or raise.

    Raises SpoofedIdentityHeader (rendered 400) when the client asserts
    identity, and Unauthenticated (401) when no server-side identity is
    available -- which is the correct state until M01 lands.

    Does not handle: session lookup. When M01 is integrated, the host passes a
    real session-derived context and this persona branch is disabled by
    configuration.
    """
    assert_no_client_identity_headers(meta)

    if dev_persona_mode == "fixed":
        if app_env == "production":
            raise Unauthenticated("error.dev_persona_forbidden_in_production")
        if not is_trusted_persona_peer(
            meta.get("REMOTE_ADDR"),  # type: ignore[arg-type]
            trusted_networks=trusted_persona_networks,
        ):
            raise Unauthenticated("error.dev_persona_requires_loopback")
        if persona is None:
            raise Unauthenticated("error.dev_persona_not_configured")
        return build_dev_context(persona, clock=clock)

    raise Unauthenticated("error.unauthenticated")
