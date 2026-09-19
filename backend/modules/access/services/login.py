"""Login, the 2FA challenge, and recovery-code sign-in.

The shape that matters: a correct password yields a CHALLENGE, not a session. The
challenge is useless on its own -- no business endpoint accepts it and no cookie is
issued -- so a stolen password alone cannot reach any data.

An unknown login and a wrong password are indistinguishable, and both cost the same
password-hash work, so accounts cannot be enumerated by response or by timing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import F

from contracts.errors import StateConflict, Unauthenticated, ValidationFailed

from ..models.accounts import FactorState
from . import sessions, throttle
from .crypto import hash_recovery_code
from .totp import TotpVerificationError, accept_code

#: How long a pre-authentication challenge lives. Five minutes, as proposed.
CHALLENGE_LIFETIME_SECONDS = 300

#: Failed code attempts allowed against ONE challenge before it is invalidated.
#: Invalidating the challenge -- not the account -- is what keeps this from being a
#: denial-of-service an attacker can trigger against a victim.
CHALLENGE_ATTEMPT_LIMIT = 5

#: A dummy hash, compared against when the account does not exist so that the
#: response time does not reveal whether a login name is real.
_DUMMY_HASH = make_password("dummy-password-for-constant-time-comparison")


@dataclass(frozen=True, slots=True)
class ChallengeIssued:
    """The result of a successful password step."""

    challenge_id: object
    expires_at: datetime
    next_action: str


class NextAction:
    """What the client must do after the password step."""

    TOTP_REQUIRED = "totp_required"
    ENROL_REQUIRED = "enrol_factor_required"
    AUTHENTICATED = "authenticated"


def begin_login(
    *,
    school_id,
    login_name: str,
    password: str,
    instant: datetime,
    remote_addr: str,
) -> tuple[ChallengeIssued, object]:
    """Verify a password and issue a pre-authentication challenge.

    Returns the challenge and the User. Raises Unauthenticated with ONE message key
    for both an unknown login and a wrong password, and RateLimited when either the
    per-account or the per-address counter is over its limit.

    Throttles are enforced BEFORE the hash comparison, which also removes the timing
    signal that would otherwise distinguish a throttled account from a missing one.
    """
    from ..models import LoginChallenge, User

    account_counter = throttle.account_key(school_id, login_name)
    address_counter = throttle.address_key(remote_addr)
    throttle.enforce(account_counter, throttle.ACCOUNT_FAILURE_LIMIT)
    throttle.enforce(address_counter, throttle.ADDRESS_FAILURE_LIMIT)

    user = User.objects.filter(
        school_id=school_id, login_name__iexact=login_name.strip()
    ).first()

    # Always do the hash work, even with no account, so the two cases cost the same.
    stored_hash = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = check_password(password, stored_hash)

    if user is None or not password_ok or not user.active:
        throttle.record_failure(account_counter)
        throttle.record_failure(address_counter)
        raise Unauthenticated("error.challenge_invalid")

    throttle.clear(account_counter)

    challenge = LoginChallenge.objects.create(
        school_id=user.school_id,
        user=user,
        created_at=instant,
        expires_at=instant + timedelta(seconds=CHALLENGE_LIFETIME_SECONDS),
    )
    return (
        ChallengeIssued(
            challenge_id=challenge.id,
            expires_at=challenge.expires_at,
            next_action=_next_action_for(user),
        ),
        user,
    )


def _next_action_for(user) -> str:
    """Decide what the account must do next.

    An account whose role requires a factor but has none must ENROL before it can
    sign in -- it is never quietly admitted with a password-only session. An account
    with no requirement and no factor is authenticated by the password alone, which
    is the school-configurable parent/student path.
    """
    from ..models import TotpFactor

    has_active = TotpFactor.objects.filter(user=user, state=FactorState.ACTIVE).exists()
    if has_active:
        return NextAction.TOTP_REQUIRED
    if two_factor_required_for(user):
        return NextAction.ENROL_REQUIRED
    return NextAction.AUTHENTICATED


def two_factor_required_for(user) -> bool:
    """Return whether policy requires a second factor for this account.

    Derived from the account's ROLES, never from a hard-coded username. Parent and
    student enforcement is school-configurable and ships OFF, so it appears here
    only as a role flag a school can set.
    """
    from ..models import Role

    return Role.objects.filter(user_links__user=user, requires_two_factor=True).exists()


def load_open_challenge(challenge_id, *, instant: datetime):
    """Return a usable challenge, or raise.

    Raises Unauthenticated with ``error.challenge_expired`` when past expiry, and
    ``error.challenge_invalid`` for unknown, consumed or over-attempt challenges --
    one key for all three, so challenge ids cannot be probed.
    """
    from ..models import LoginChallenge

    challenge = LoginChallenge.objects.select_related("user").filter(id=challenge_id).first()
    if challenge is None or challenge.consumed_at is not None:
        raise Unauthenticated("error.challenge_invalid")
    if challenge.attempts >= CHALLENGE_ATTEMPT_LIMIT:
        raise Unauthenticated("error.challenge_invalid")
    if instant >= challenge.expires_at:
        raise Unauthenticated("error.challenge_expired")
    return challenge


def record_failed_attempt(challenge_id, *, reason: str) -> None:
    """Increment a challenge's attempt counter in its OWN transaction.

    This must not run inside the caller's transaction. The original version
    incremented the counter and then raised, which rolled the increment back with
    everything else -- so the counter never advanced, the challenge was never
    invalidated, and an attacker had unlimited attempts against a single challenge.
    A test caught it; the symptom was a 422 where a 401 was expected.

    Uses F() so two concurrent wrong guesses both count.
    """
    from ..models import LoginChallenge

    with transaction.atomic():
        LoginChallenge.objects.filter(id=challenge_id).update(attempts=F("attempts") + 1)
        LoginChallenge.objects.filter(
            id=challenge_id, attempts__gte=CHALLENGE_ATTEMPT_LIMIT
        ).update(invalidated_reason=reason)


def verify_totp_and_authenticate(
    *,
    challenge_id,
    code: str,
    instant: datetime,
    remote_addr: str,
    user_agent: str = "",
) -> sessions.IssuedSession:
    """Complete a challenge with a TOTP code and return a live session.

    Consumes the challenge and creates the session in ONE transaction, so a failure
    anywhere leaves neither a spent challenge nor a session. The TOTP step is itself
    atomic against replay.
    """
    from ..models import TotpFactor

    address_counter = throttle.address_key(remote_addr)
    throttle.enforce(address_counter, throttle.ADDRESS_FAILURE_LIMIT)

    # Checked before opening the transaction, so an over-attempt challenge is
    # refused without taking a row lock.
    load_open_challenge(challenge_id, instant=instant)

    try:
        with transaction.atomic():
            challenge = load_open_challenge(challenge_id, instant=instant)
            factor = (
                TotpFactor.objects.select_for_update()
                .filter(user=challenge.user, state=FactorState.ACTIVE)
                .first()
            )
            if factor is None:
                raise StateConflict("error.factor_already_active")
            accept_code(factor, code, instant=instant)
            challenge.consumed_at = instant
            challenge.save(update_fields=["consumed_at"])
            issued = sessions.create_session(
                user=challenge.user,
                auth_level=sessions.AUTH_LEVEL_PASSWORD_TOTP,
                instant=instant,
                user_agent=user_agent,
                challenge_id=challenge.id,
            )
    except TotpVerificationError as exc:
        # Outside the rolled-back transaction, so the counter actually advances.
        record_failed_attempt(challenge_id, reason="attempt_limit")
        throttle.record_failure(address_counter)
        raise ValidationFailed("error.totp_code_invalid") from exc

    throttle.clear(address_counter)
    return issued


def authenticate_without_factor(
    *, challenge_id, instant: datetime, user_agent: str = ""
) -> sessions.IssuedSession:
    """Complete a challenge for an account that policy does not require a factor for.

    Refuses when the account DOES require one, so this cannot be used as a bypass.
    """
    with transaction.atomic():
        challenge = load_open_challenge(challenge_id, instant=instant)
        if two_factor_required_for(challenge.user):
            raise StateConflict("error.factor_already_active")
        challenge.consumed_at = instant
        challenge.save(update_fields=["consumed_at"])
        return sessions.create_session(
            user=challenge.user,
            auth_level=sessions.AUTH_LEVEL_PASSWORD,
            instant=instant,
            user_agent=user_agent,
            challenge_id=challenge.id,
        )


def recover_with_code(
    *,
    challenge_id,
    recovery_code: str,
    instant: datetime,
    remote_addr: str,
    user_agent: str = "",
) -> tuple[sessions.IssuedSession, object]:
    """Consume a recovery code and return a recovery-level session.

    The consumption is a CONDITIONAL UPDATE whose row count is checked, so two
    concurrent requests presenting the same code resolve to exactly one winner and
    the loser gets 409. Revokes existing sessions and the old factor, because a
    recovery implies the factor is no longer trustworthy.

    The returned session is RECOVERY level: it permits factor re-enrolment and
    nothing else. There is no SMS fallback anywhere in this path.
    """
    address_counter = throttle.address_key(remote_addr)
    throttle.enforce(address_counter, throttle.ADDRESS_FAILURE_LIMIT)

    try:
        return _consume_recovery_code(
            challenge_id=challenge_id,
            recovery_code=recovery_code,
            instant=instant,
            user_agent=user_agent,
            address_counter=address_counter,
        )
    except _UnknownRecoveryCode as exc:
        record_failed_attempt(challenge_id, reason="recovery_attempt_limit")
        throttle.record_failure(address_counter)
        raise ValidationFailed("error.totp_code_invalid") from exc


class _UnknownRecoveryCode(Exception):
    """Internal signal: the code did not match. Never leaves this module."""


def _consume_recovery_code(
    *, challenge_id, recovery_code: str, instant: datetime, user_agent: str, address_counter
) -> tuple[sessions.IssuedSession, object]:
    """Consume a recovery code inside one transaction. See recover_with_code."""
    from ..models import RecoveryCode, TotpFactor

    with transaction.atomic():
        challenge = load_open_challenge(challenge_id, instant=instant)
        user = challenge.user
        code_hash = hash_recovery_code(recovery_code, school_id=user.school_id)

        candidate = RecoveryCode.objects.filter(user=user, code_hash=code_hash).first()
        if candidate is None:
            # Raised INSIDE the transaction, so the counter is bumped after it
            # unwinds -- see record_failed_attempt. Flagged here rather than
            # incremented inline, which would roll back with everything else.
            raise _UnknownRecoveryCode

        # Atomic single-use consumption. Only one concurrent caller can match
        # used_at IS NULL, so exactly one succeeds.
        consumed = RecoveryCode.objects.filter(pk=candidate.pk, used_at__isnull=True).update(
            used_at=instant
        )
        if consumed != 1:
            raise StateConflict("error.recovery_code_already_used")

        challenge.consumed_at = instant
        challenge.save(update_fields=["consumed_at"])

        # A recovery means the factor is not trustworthy: revoke it and every
        # session it authorised, so the old authenticator is dead.
        TotpFactor.objects.filter(user=user, state=FactorState.ACTIVE).update(
            state=FactorState.REVOKED, revoked_at=instant
        )
        sessions.revoke_all_for_user(user, instant=instant)

        issued = sessions.create_session(
            user=user,
            auth_level=sessions.AUTH_LEVEL_RECOVERY,
            instant=instant,
            user_agent=user_agent,
            challenge_id=challenge.id,
        )
        RecoveryCode.objects.filter(pk=candidate.pk).update(
            used_by_session_id=issued.session_id
        )
        throttle.clear(address_counter)
        return issued, user


def confirm_password(*, user, password: str, instant: datetime) -> None:
    """Re-verify a password and record the confirmation time.

    Required before factor enrolment, replacement or disable. Raises Unauthenticated
    rather than a validation error, because the remedy is to authenticate again.
    """
    if not check_password(password, user.password_hash):
        raise Unauthenticated("error.password_confirmation_required")
    user.password_confirmed_at = instant
    user.save(update_fields=["password_confirmed_at"])


def require_recent_password_confirmation(
    *, user, instant: datetime, max_age_seconds: int = 300
) -> None:
    """Raise unless the password was confirmed within the window."""
    confirmed = user.password_confirmed_at
    if confirmed is None or (instant - confirmed) > timedelta(seconds=max_age_seconds):
        raise Unauthenticated("error.password_confirmation_required")
