"""Plain helpers for M01's suite. Not fixtures -- imported directly by tests.

Named ``m01_helpers`` rather than ``helpers`` because pytest's prepend import mode
cannot hold two modules of the same basename from different directories, and every
module will want helpers of its own.
"""

from __future__ import annotations

import uuid
from datetime import datetime

#: The passwords the seed uses. Test-only values that exist nowhere else.
PASSWORDS = {
    "o1": "Owner-O1-test-only",
    "t1": "Teacher-T1-test-only",
    "g1": "Guardian-G1-test-only",
    "p1": "Principal-P1-test-only",
    "o2_school_b": "Owner-O2-test-only",
}
LOGINS = {
    "o1": "owner.o1",
    "t1": "teacher.t1",
    "g1": "guardian.g1",
    "p1": "principal.p1",
    "o2_school_b": "owner.o2",
}


def totp_code_for(user, *, instant: datetime) -> str:
    """Return a currently-valid TOTP code for an account's active factor."""
    import pyotp

    from modules.access.models import TotpFactor
    from modules.access.models.accounts import FactorState
    from modules.access.services.crypto import decrypt_secret
    from modules.access.services.totp import TOTP_DIGITS, TOTP_PERIOD_SECONDS, current_step

    factor = TotpFactor.objects.get(user=user, state=FactorState.ACTIVE)
    secret = decrypt_secret(factor.encrypted_secret)
    return pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_PERIOD_SECONDS).generate_otp(
        current_step(instant)
    )


def enrol_and_activate(api, user, label: str, clock) -> tuple[str, ...]:
    """Take an account through the full enrolment and return its recovery codes."""
    import pyotp

    from modules.access.services.totp import TOTP_DIGITS, TOTP_PERIOD_SECONDS, current_step

    login = api.post("/auth/login", {"login_name": LOGINS[label], "password": PASSWORDS[label]})
    assert login.status_code == 201, login.content
    challenge_id = login.json()["challenge_id"]
    start = api.post(
        "/auth/2fa/enroll",
        {"password": PASSWORDS[label], "challenge_id": challenge_id},
    )
    assert start.status_code == 201, start.content
    secret = start.json()["secret_base32"]
    code = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_PERIOD_SECONDS).generate_otp(
        current_step(clock.now())
    )
    confirm = api.post(
        "/auth/2fa/confirm",
        {
            "factor_id": start.json()["factor_id"],
            "code": code,
            "password": PASSWORDS[label],
            "challenge_id": challenge_id,
        },
    )
    assert confirm.status_code == 201, confirm.content
    # Confirming the factor CONSUMED this time step (that is the replay
    # protection), so advance past it. Otherwise the very next login with a code
    # from the same step is correctly refused -- which surprised this test before
    # it surprised a user.
    clock.advance(seconds=31)
    return tuple(confirm.json()["codes"])


def new_uuid() -> uuid.UUID:
    """Return a random uuid, for negative tests needing an unknown id."""
    return uuid.uuid4()
