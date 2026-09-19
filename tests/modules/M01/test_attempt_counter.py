"""Prove the attempt counter survives the rolled-back transaction."""
import pytest
from m01_helpers import LOGINS, PASSWORDS, enrol_and_activate

pytestmark = [pytest.mark.django_db, pytest.mark.module]


def test_attempt_counter_persists_across_failed_attempts(api, seeded, clock):
    from modules.access.models import LoginChallenge

    enrol_and_activate(api, seeded["t1"], "t1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    challenge_id = login.json()["challenge_id"]

    observed = []
    for _ in range(5):
        api.post("/auth/2fa/verify", {"challenge_id": challenge_id, "code": "000000"})
        observed.append(LoginChallenge.objects.get(id=challenge_id).attempts)
    print("\n  attempts after each failure:", observed)
    assert observed == [1, 2, 3, 4, 5], "counter must advance and persist"

    row = LoginChallenge.objects.get(id=challenge_id)
    print("  invalidated_reason:", repr(row.invalidated_reason))
    assert row.invalidated_reason == "attempt_limit"
    assert api.post("/auth/2fa/verify", {"challenge_id": challenge_id, "code": "000000"}).status_code == 401
    print("  6th attempt: 401, challenge dead")
