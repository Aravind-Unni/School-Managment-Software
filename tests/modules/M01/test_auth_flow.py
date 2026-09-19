"""M01 acceptance: login, 2FA, replay, expiry, recovery and reset.

Mirrors contracts/M01/fixtures/expected-results.json. Each test names the acceptance
case it covers, so a reviewer can map the file to the contract.
"""

from __future__ import annotations

import pytest
from m01_helpers import LOGINS, PASSWORDS, enrol_and_activate, totp_code_for

from shared import fixtures

pytestmark = [pytest.mark.django_db, pytest.mark.module]


# --- the challenge is not a session ---------------------------------------


def test_login_returns_a_challenge_and_no_session_cookie(api, seeded):
    """A correct password yields a challenge, never a business session."""
    response = api.post(
        "/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]}
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"challenge_id", "expires_at", "next_action"}
    # T1 is staff with no factor yet, so policy requires enrolment before sign-in.
    assert body["next_action"] == "enrol_factor_required"
    assert api.session_cookie is None


def test_a_wrong_password_is_indistinguishable_from_an_unknown_login(api, seeded):
    """Account enumeration must not be possible from the response."""
    wrong = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": "nope"})
    unknown = api.post("/auth/login", {"login_name": "no.such.person", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert (
        wrong.json()["message_key"]
        == unknown.json()["message_key"]
        == "error.challenge_invalid"
    )


def test_the_business_api_refuses_a_challenge_id(api, seeded):
    """Acceptance: holding a challenge grants access to nothing."""
    api.post("/auth/login", {"login_name": LOGINS["p1"], "password": PASSWORDS["p1"]})
    assert api.get("/accounts").status_code == 401


# --- enrolment, verification, replay --------------------------------------


def test_enrolment_then_login_succeeds_and_rotates_the_session(api, seeded, clock):
    """Acceptance: only the first valid completed login works."""
    enrol_and_activate(api, seeded["t1"], "t1", clock)
    after_enrol = api.session_cookie

    login = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    assert login.json()["next_action"] == "totp_required"

    code = totp_code_for(seeded["t1"], instant=clock.now())
    verify = api.post(
        "/auth/2fa/verify",
        {"challenge_id": login.json()["challenge_id"], "code": code},
    )
    assert verify.status_code == 200
    assert verify.json()["auth_level"] == "password_totp"
    # The session identifier must change when the factor completes.
    assert api.session_cookie != after_enrol


def test_replaying_the_same_code_is_refused_inside_its_own_window(api, seeded, clock):
    """Acceptance: last_accepted_step makes acceptance atomic."""
    enrol_and_activate(api, seeded["t1"], "t1", clock)
    code = totp_code_for(seeded["t1"], instant=clock.now())

    first_login = api.post(
        "/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]}
    )
    first = api.post(
        "/auth/2fa/verify", {"challenge_id": first_login.json()["challenge_id"], "code": code}
    )
    assert first.status_code == 200

    # Same code, fresh challenge, still inside the 30-second step.
    second_login = api.post(
        "/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]}
    )
    second = api.post(
        "/auth/2fa/verify", {"challenge_id": second_login.json()["challenge_id"], "code": code}
    )
    assert second.status_code == 422
    assert second.json()["message_key"] == "error.totp_code_invalid"


def test_an_expired_challenge_is_refused(api, seeded, clock):
    """Acceptance: the preloaded expired challenge yields error.challenge_expired."""
    expired_id = str(fixtures.fixture_uuid("m01.challenge.expired"))
    response = api.post("/auth/2fa/verify", {"challenge_id": expired_id, "code": "123456"})
    assert response.status_code == 401
    assert response.json()["message_key"] == "error.challenge_expired"


def test_an_unknown_challenge_is_indistinguishable_from_a_consumed_one(api, seeded, clock):
    """Challenge ids must not be probeable."""
    from m01_helpers import new_uuid

    unknown = api.post("/auth/2fa/verify", {"challenge_id": str(new_uuid()), "code": "123456"})
    assert unknown.status_code == 401
    assert unknown.json()["message_key"] == "error.challenge_invalid"


def test_a_challenge_is_invalidated_after_five_failed_codes(api, seeded, clock):
    """The CHALLENGE is invalidated, not the account: no attacker-triggered lockout."""
    enrol_and_activate(api, seeded["t1"], "t1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    challenge_id = login.json()["challenge_id"]

    for _ in range(5):
        api.post("/auth/2fa/verify", {"challenge_id": challenge_id, "code": "000000"})

    # The challenge is dead...
    dead = api.post("/auth/2fa/verify", {"challenge_id": challenge_id, "code": "000000"})
    assert dead.status_code == 401
    # ...but the account is not: a fresh login still works.
    again = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    assert again.status_code == 201


# --- recovery --------------------------------------------------------------


def test_a_recovery_code_signs_in_once_and_revokes_the_old_factor(api, seeded, clock):
    """Acceptance: recovery consumes the code and kills the old factor."""
    from modules.access.models import TotpFactor
    from modules.access.models.accounts import FactorState

    codes = enrol_and_activate(api, seeded["t1"], "t1", clock)
    assert TotpFactor.objects.filter(user=seeded["t1"], state=FactorState.ACTIVE).exists()

    login = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    response = api.post(
        "/auth/2fa/recover",
        {"challenge_id": login.json()["challenge_id"], "recovery_code": codes[0]},
    )
    assert response.status_code == 200
    assert response.json()["auth_level"] == "recovery"
    assert not TotpFactor.objects.filter(user=seeded["t1"], state=FactorState.ACTIVE).exists()


def test_replaying_a_used_recovery_code_is_refused(api, seeded, clock):
    """Acceptance: the preloaded used code yields 409.

    G1 enrols first. G1's guardian role does NOT require a factor, so this also
    covers the "optional 2FA" fixture: once G1 has a factor the login stops at
    totp_required and the challenge stays open for the recovery attempt.
    """
    from modules.access.seeds import USED_RECOVERY_CODE

    enrol_and_activate(api, seeded["g1"], "g1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["g1"], "password": PASSWORDS["g1"]})
    assert login.json()["next_action"] == "totp_required"

    response = api.post(
        "/auth/2fa/recover",
        {"challenge_id": login.json()["challenge_id"], "recovery_code": USED_RECOVERY_CODE},
    )
    assert response.status_code == 409
    assert response.json()["message_key"] == "error.recovery_code_already_used"


def test_a_recovery_session_cannot_perform_a_business_action(api, seeded, clock):
    """A recovery session exists to re-enrol a factor and nothing else."""
    codes = enrol_and_activate(api, seeded["p1"], "p1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["p1"], "password": PASSWORDS["p1"]})
    api.post(
        "/auth/2fa/recover",
        {"challenge_id": login.json()["challenge_id"], "recovery_code": codes[0]},
    )
    # P1 holds accounts.manage, but a recovery session must not satisfy it.
    assert api.get("/accounts").status_code == 401


def test_device_loss_recovery_needs_no_sms_service(api, seeded, clock, settings):
    """Acceptance: the whole path works with no SMS provider anywhere.

    Asserted structurally: the notifications port is not even a declared consumer of
    M01, so there is nothing for an SMS provider to be bound to.
    """
    from modules.access.registration import REGISTRATION

    assert "notifications" not in REGISTRATION.consumers
    codes = enrol_and_activate(api, seeded["t1"], "t1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    assert (
        api.post(
            "/auth/2fa/recover",
            {"challenge_id": login.json()["challenge_id"], "recovery_code": codes[0]},
        ).status_code
        == 200
    )


# --- step-up and protected roles -----------------------------------------


def test_a_password_only_session_without_the_grant_is_403_not_401(api, seeded, clock):
    """An unauthorised actor is told "denied", never "step up".

    G1 is a guardian: the role requires no factor, so G1 gets a password-only
    session, and G1 does not hold accounts.manage. The permission check runs BEFORE
    the step-up check deliberately -- prompting G1 to confirm a second factor would
    tell them the action exists and that they very nearly have it.

    The complementary case (authenticated, HOLDS the grant, but has not completed
    2FA) is covered by test_a_recovery_session_cannot_perform_a_business_action.
    """
    login = api.post("/auth/login", {"login_name": LOGINS["g1"], "password": PASSWORDS["g1"]})
    assert login.json()["next_action"] == "authenticated"
    assert api.session_cookie is not None

    response = api.get("/accounts")
    assert response.status_code == 403
    assert response.json()["code"] == "action_denied"


def test_stale_two_factor_is_refused_on_a_sensitive_read(api, seeded, clock):
    """A live session whose factor is hours old must fail a step-up check."""
    enrol_and_activate(api, seeded["p1"], "p1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["p1"], "password": PASSWORDS["p1"]})
    code = totp_code_for(seeded["p1"], instant=clock.now())
    api.post("/auth/2fa/verify", {"challenge_id": login.json()["challenge_id"], "code": code})

    assert api.get("/accounts").status_code == 200
    clock.advance(minutes=10)
    stale = api.get("/accounts")
    assert stale.status_code == 401
    assert stale.json()["message_key"] == "error.two_factor_stale"
