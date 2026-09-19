"""Session creation, rotation, lookup and revocation.

Rules enforced here:
  * The token is returned to the client once; only its hash is stored.
  * Completing a factor ROTATES the session identifier, so a token observed
    during the password step cannot be used after the factor succeeds.
  * ``auth_time`` records when the factor was asserted, not when the session
    began, so a long-lived session still fails a step-up check.
  * A revoked session is never resurrected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contracts.identity import AuthLevel, RequestContext

from ..models.accounts import AuthLevelChoices
from .authorize import auth_level_from_session
from .crypto import hash_session_token, new_session_token

#: Coarse client families for the active-sessions screen. The raw User-Agent is
#: deliberately not stored: it is a fingerprinting surface with no user benefit.
_AGENT_FAMILIES: tuple[tuple[str, str], ...] = (
    ("Edg", "Edge"),
    ("OPR", "Opera"),
    ("Chrome", "Chrome"),
    ("Safari", "Safari"),
    ("Firefox", "Firefox"),
    ("curl", "curl"),
    ("python", "script"),
)


def agent_family(user_agent: str) -> str:
    """Return a coarse client family from a User-Agent string.

    Order matters: Edge and Opera both advertise Chrome, and Chrome advertises
    Safari, so the more specific tokens are checked first.
    """
    for token, family in _AGENT_FAMILIES:
        if token.lower() in (user_agent or "").lower():
            return family
    return "unknown"


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """A newly created session and its one-time token."""

    session_id: UUID
    token: str
    auth_level: str
    auth_time: datetime


def create_session(
    *,
    user,
    auth_level: str,
    instant: datetime,
    user_agent: str = "",
    challenge_id: UUID | None = None,
) -> IssuedSession:
    """Create a session and return it with its plaintext token.

    The plaintext is returned ONLY here. Callers must put it in a
    Secure/HttpOnly/SameSite cookie and never log it.
    """
    from ..models import Session

    token = new_session_token()
    session = Session.objects.create(
        school_id=user.school_id,
        user=user,
        token_hash=hash_session_token(token),
        auth_level=auth_level,
        auth_time=instant,
        created_at=instant,
        last_seen_at=instant,
        user_agent_family=agent_family(user_agent),
        created_by_challenge_id=challenge_id,
    )
    return IssuedSession(
        session_id=session.id,
        token=token,
        auth_level=auth_level,
        auth_time=instant,
    )


def rotate_session(*, old_session, user, auth_level: str, instant: datetime) -> IssuedSession:
    """Revoke a session and issue a fresh one with a new token.

    Rotation on privilege change is the point: an attacker who captured the
    password-step token holds a revoked session once the factor completes.
    """
    revoke_session(old_session, instant=instant)
    return create_session(
        user=user,
        auth_level=auth_level,
        instant=instant,
        user_agent=old_session.user_agent_family,
        challenge_id=old_session.created_by_challenge_id,
    )


def revoke_session(session, *, instant: datetime) -> None:
    """Mark a session revoked. Idempotent.

    Never clears ``revoked_at`` once set: a revoked session must stay revoked even
    if a later code path tries to reuse the row.
    """
    if session.revoked_at is None:
        session.revoked_at = instant
        session.save(update_fields=["revoked_at"])


def revoke_all_for_user(
    user, *, instant: datetime, except_session_id: UUID | None = None
) -> int:
    """Revoke every live session for an account and return how many were revoked.

    Used by factor reset and recovery: a lost or replaced factor must invalidate
    every session that the old factor authorised, or the reset achieves nothing.
    """
    from ..models import Session

    queryset = Session.objects.filter(user=user, revoked_at__isnull=True)
    if except_session_id is not None:
        queryset = queryset.exclude(id=except_session_id)
    return queryset.update(revoked_at=instant)


def resolve_session(token: str, *, instant: datetime):
    """Return the live Session for a token, or None.

    Looks up by HASH, so a leaked database row yields no usable token. A revoked
    session resolves to None. Also refreshes ``last_seen_at``, which is what makes
    the active-sessions screen meaningful.
    """
    from ..models import Session

    if not token:
        return None
    session = (
        Session.objects.select_related("user")
        .filter(token_hash=hash_session_token(token), revoked_at__isnull=True)
        .first()
    )
    if session is None:
        return None
    # A session belonging to a deactivated account is not usable, even though the
    # row is still live: deactivation must take effect without a sweep job.
    if not session.user.active:
        return None
    Session.objects.filter(pk=session.pk).update(last_seen_at=instant)
    session.last_seen_at = instant
    return session


def context_from_session(session, *, request_id: str) -> RequestContext:
    """Build the trusted RequestContext for a live session.

    The school comes from the SESSION ROW, never from the request, which is what
    makes "do not trust client school claims" structural rather than a convention.

    A recovery session maps to AuthLevel.PASSWORD deliberately: it must never
    satisfy a two-factor requirement, since it exists only to re-enrol a factor.
    """
    return RequestContext(
        actor_id=session.user_id,
        school_id=session.school_id,
        request_id=request_id,
        auth_level=auth_level_from_session(session.auth_level),
        auth_time=session.auth_time,
    )


def describe_session(session, *, current_session_id: UUID | None) -> dict[str, object]:
    """Serialise a session for the caller's own active-sessions list."""
    return {
        "id": str(session.id),
        "auth_level": session.auth_level,
        "auth_time": session.auth_time.isoformat(),
        "created_at": session.created_at.isoformat(),
        "last_seen_at": session.last_seen_at.isoformat(),
        "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
        "is_current": session.id == current_session_id,
        "user_agent_family": session.user_agent_family,
    }


#: Re-exported so views need not reach into the models package for the enum.
AUTH_LEVEL_PASSWORD = AuthLevelChoices.PASSWORD
AUTH_LEVEL_PASSWORD_TOTP = AuthLevelChoices.PASSWORD_TOTP
AUTH_LEVEL_RECOVERY = AuthLevelChoices.RECOVERY

#: Shared AuthLevel equivalents, for callers that compare against the contract.
SHARED_LEVELS: dict[str, AuthLevel] = {
    AuthLevelChoices.PASSWORD: AuthLevel.PASSWORD,
    AuthLevelChoices.PASSWORD_TOTP: AuthLevel.TWO_FACTOR,
    AuthLevelChoices.RECOVERY: AuthLevel.PASSWORD,
}
