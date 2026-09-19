"""RFC 6238 TOTP verification with atomic replay protection.

Profile, as proposed by M01: six digits, a 30-second step, and at most ONE
adjacent step of drift either side.

Replay protection is the part worth reading carefully. Checking a code against
the current window is not enough: within one 30-second step the same code is
valid many times, so an attacker who observes a code can reuse it immediately. A
code is therefore accepted only if its time step is strictly greater than the
last step this factor accepted, and that comparison happens as a CONDITIONAL
DATABASE UPDATE whose row count is checked. Two concurrent requests with the same
code cannot both win, because only one UPDATE can match.

Uses ``pyotp``, a maintained RFC 6238 implementation, rather than hand-rolled
HMAC. TOTP is not phishing resistant; passkeys are a separate evaluation.

Does not handle: rate limiting (see ``services/throttle.py``) or deciding whether
an action needs a factor at all (see ``services/authorize.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyotp
from django.db.models import Q

from .crypto import constant_time_equals, decrypt_secret

#: The proposed profile. These are data, not scattered literals, so changing the
#: profile is one reviewed edit.
TOTP_DIGITS = 6
TOTP_PERIOD_SECONDS = 30
#: How many steps of clock drift to tolerate either side of the current step.
#: One step (30s) is the OWASP-aligned compromise between phone clock skew and
#: the window an observed code stays usable.
TOTP_DRIFT_STEPS = 1


class TotpVerificationError(Exception):
    """A code did not verify. Carries no detail about why, by design.

    The caller maps this to one message key regardless of cause, so a client
    cannot distinguish "wrong code" from "replayed code" from "outside window".
    """


@dataclass(frozen=True, slots=True)
class VerifiedCode:
    """A successfully verified code and the time step it belonged to."""

    step: int
    drift_steps: int


def current_step(instant: datetime) -> int:
    """Return the RFC 6238 time step for an instant.

    Assumes ``instant`` is timezone-aware. Uses the Unix timestamp, so the school
    timezone is irrelevant here -- TOTP is defined against UTC epoch seconds.
    """
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    return int(instant.timestamp()) // TOTP_PERIOD_SECONDS


def provisioning_uri(secret_base32: str, *, account_name: str, issuer: str) -> str:
    """Return the otpauth:// URI for an authenticator app.

    The caller must treat this as secret: it embeds the seed. It is returned to the
    enrolling user exactly once and never logged.
    """
    return pyotp.TOTP(
        secret_base32, digits=TOTP_DIGITS, interval=TOTP_PERIOD_SECONDS
    ).provisioning_uri(name=account_name, issuer_name=issuer)


def match_code(secret_base32: str, code: str, *, instant: datetime) -> VerifiedCode:
    """Return the time step a code belongs to, or raise TotpVerificationError.

    Checks the current step and ``TOTP_DRIFT_STEPS`` either side, comparing in
    constant time so a near-miss cannot be found by timing. Does NOT consider
    replay -- that needs the stored state and happens in ``accept_code``.
    """
    if not (code.isdigit() and len(code) == TOTP_DIGITS):
        raise TotpVerificationError("malformed code")

    totp = pyotp.TOTP(secret_base32, digits=TOTP_DIGITS, interval=TOTP_PERIOD_SECONDS)
    step_now = current_step(instant)
    for drift in range(-TOTP_DRIFT_STEPS, TOTP_DRIFT_STEPS + 1):
        candidate_step = step_now + drift
        if constant_time_equals(totp.generate_otp(candidate_step), code):
            return VerifiedCode(step=candidate_step, drift_steps=drift)
    raise TotpVerificationError("no matching step")


def accept_code(factor, code: str, *, instant: datetime) -> VerifiedCode:
    """Verify a code AND consume its time step atomically.

    Raises TotpVerificationError when the code does not match, or when its step is
    not strictly newer than the last accepted one -- which is what makes a replay
    fail even inside its own 30-second window.

    The consumption is a single conditional UPDATE whose row count is checked, so
    two concurrent requests presenting the same code cannot both succeed: exactly
    one UPDATE matches the ``last_accepted_step < step`` predicate.

    Does not handle: transactions. The caller owns the transaction so that the
    audit row and the session creation commit or roll back with this.
    """
    from ..models import TotpFactor

    verified = match_code(decrypt_secret(factor.encrypted_secret), code, instant=instant)

    updated = (
        TotpFactor.objects.filter(pk=factor.pk)
        .filter(Q(last_accepted_step__isnull=True) | Q(last_accepted_step__lt=verified.step))
        .update(last_accepted_step=verified.step)
    )
    if updated != 1:
        # The step was already consumed. Either a replay, or a concurrent request
        # won the race. Indistinguishable to the caller on purpose.
        raise TotpVerificationError("step already consumed")

    factor.last_accepted_step = verified.step
    return verified
