"""M01 acceptance: concurrent single-use consumption and transaction rollback."""

from __future__ import annotations

import threading

import pytest
from m01_helpers import LOGINS, PASSWORDS, enrol_and_activate

from shared import fixtures

pytestmark = [pytest.mark.django_db, pytest.mark.module]


def test_concurrent_reuse_of_one_recovery_code_succeeds_exactly_once(api, seeded, clock):
    """Acceptance: exactly one winner.

    Exercises the mechanism directly -- two conditional UPDATEs against
    ``used_at IS NULL`` -- because that single predicate is what decides the race.
    Only one UPDATE can match, so the second caller sees rowcount 0 and gets 409.
    """
    from modules.access.models import RecoveryCode
    from modules.access.services.crypto import hash_recovery_code

    codes = enrol_and_activate(api, seeded["t1"], "t1", clock)
    target = RecoveryCode.objects.get(
        user=seeded["t1"],
        code_hash=hash_recovery_code(codes[0], school_id=fixtures.SCHOOL_A),
    )

    def attempt() -> int:
        return RecoveryCode.objects.filter(pk=target.pk, used_at__isnull=True).update(
            used_at=clock.now()
        )

    outcomes = [attempt(), attempt()]
    assert outcomes.count(1) == 1, f"exactly one winner expected, got {outcomes}"
    assert outcomes.count(0) == 1


@pytest.mark.requires_postgres
@pytest.mark.django_db(transaction=True)
def test_two_real_threads_racing_one_recovery_code(api, seeded, clock):
    """The same race with two REAL connections, contending at the same instant.

    Skipped on SQLite because an in-memory database cannot stage a genuine
    two-connection race -- but the skip is decided from the LIVE connection vendor,
    not hardcoded. An earlier version called pytest.skip() unconditionally, which
    meant the test could never run even on PostgreSQL: a marker promising coverage
    that no environment could deliver.

    Both threads wait on a barrier so they attempt the conditional UPDATE
    simultaneously, which is the only way to exercise the row-level contention
    rather than two sequential calls.
    """
    from django.db import connection, connections

    if connection.vendor != "postgresql":
        pytest.skip(f"needs PostgreSQL; this run is on {connection.vendor}")

    from modules.access.models import RecoveryCode
    from modules.access.services.crypto import hash_recovery_code

    codes = enrol_and_activate(api, seeded["t1"], "t1", clock)
    target = RecoveryCode.objects.get(
        user=seeded["t1"],
        code_hash=hash_recovery_code(codes[0], school_id=fixtures.SCHOOL_A),
    )

    barrier = threading.Barrier(2)
    outcomes: list[int] = []
    lock = threading.Lock()

    def contend() -> None:
        try:
            barrier.wait(timeout=10)
            updated = RecoveryCode.objects.filter(pk=target.pk, used_at__isnull=True).update(
                used_at=clock.now()
            )
            with lock:
                outcomes.append(updated)
        finally:
            # Each thread owns its own connection and must close it, or the test
            # database cannot be torn down.
            connections.close_all()

    threads = [threading.Thread(target=contend) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == [0, 1], f"exactly one thread must win the race, got {outcomes}"
    target.refresh_from_db()
    assert target.used_at is not None


def test_a_failed_recovery_leaves_the_code_unused(api, seeded, clock):
    """A rolled-back attempt must not consume the code."""
    from modules.access.models import RecoveryCode
    from modules.access.services.crypto import hash_recovery_code

    codes = enrol_and_activate(api, seeded["t1"], "t1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})

    # A wrong code must not spend a real one.
    bad = api.post(
        "/auth/2fa/recover",
        {"challenge_id": login.json()["challenge_id"], "recovery_code": "AAAAA-AAAAA"},
    )
    assert bad.status_code == 422
    assert RecoveryCode.objects.filter(user=seeded["t1"], used_at__isnull=True).count() == 10

    # The real one still works afterwards.
    login2 = api.post("/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]})
    good = api.post(
        "/auth/2fa/recover",
        {"challenge_id": login2.json()["challenge_id"], "recovery_code": codes[0]},
    )
    assert good.status_code == 200
    assert (
        RecoveryCode.objects.get(
            user=seeded["t1"],
            code_hash=hash_recovery_code(codes[0], school_id=fixtures.SCHOOL_A),
        ).used_at
        is not None
    )


def test_a_factor_reset_revokes_every_session(api, seeded, clock):
    """Acceptance: factor reset revokes old sessions, and emits FactorReset.v1."""
    from modules.access.models import Session, TotpFactor
    from modules.access.models.accounts import FactorState
    from shared.harness.models import HarnessOutboxEvent

    # T1 gets two live sessions.
    first = api
    enrol_and_activate(first, seeded["t1"], "t1", clock)
    second = api.__class__()
    login = second.post(
        "/auth/login", {"login_name": LOGINS["t1"], "password": PASSWORDS["t1"]}
    )
    from m01_helpers import totp_code_for

    clock.advance(seconds=31)
    second.post(
        "/auth/2fa/verify",
        {
            "challenge_id": login.json()["challenge_id"],
            "code": totp_code_for(seeded["t1"], instant=clock.now()),
        },
    )
    live_before = Session.objects.filter(user=seeded["t1"], revoked_at__isnull=True).count()
    assert live_before >= 2

    # P1 approves the seeded lost-device case.
    approver = api.__class__()
    enrol_and_activate(approver, seeded["p1"], "p1", clock)
    p1_login = approver.post(
        "/auth/login", {"login_name": LOGINS["p1"], "password": PASSWORDS["p1"]}
    )
    clock.advance(seconds=31)
    approver.post(
        "/auth/2fa/verify",
        {
            "challenge_id": p1_login.json()["challenge_id"],
            "code": totp_code_for(seeded["p1"], instant=clock.now()),
        },
    )

    case_id = fixtures.fixture_uuid("m01.case.t1_lost_device")
    response = approver.post(f"/auth/factor/reset-requests/{case_id}/approve")
    assert response.status_code == 200, response.content
    assert response.json()["state"] == "approved"

    assert Session.objects.filter(user=seeded["t1"], revoked_at__isnull=True).count() == 0
    assert not TotpFactor.objects.filter(user=seeded["t1"], state=FactorState.ACTIVE).exists()
    events = HarnessOutboxEvent.objects.filter(event_type="FactorReset.v1")
    assert events.count() == 1
    assert "password" not in repr(events.first().payload).lower()


def test_an_approver_cannot_approve_their_own_case(api, seeded, clock):
    """The second-person check is the whole point of a case."""
    from m01_helpers import totp_code_for

    from modules.access.models import RecoveryCase
    from modules.access.models.accounts import CaseState

    enrol_and_activate(api, seeded["p1"], "p1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["p1"], "password": PASSWORDS["p1"]})
    clock.advance(seconds=31)
    api.post(
        "/auth/2fa/verify",
        {
            "challenge_id": login.json()["challenge_id"],
            "code": totp_code_for(seeded["p1"], instant=clock.now()),
        },
    )
    own_case = RecoveryCase.objects.create(
        school_id=fixtures.SCHOOL_A,
        user=seeded["p1"],
        reason="Synthetic self-approval attempt",
        state=CaseState.PENDING,
        created_at=clock.now(),
    )
    response = api.post(f"/auth/factor/reset-requests/{own_case.id}/approve")
    assert response.status_code == 403


def test_audit_rows_accompany_a_committed_write(api, seeded, clock):
    """Audit participates in the caller's transaction."""
    from m01_helpers import totp_code_for

    from shared.harness.models import HarnessAuditRecord

    enrol_and_activate(api, seeded["o1"], "o1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["o1"], "password": PASSWORDS["o1"]})
    clock.advance(seconds=31)
    api.post(
        "/auth/2fa/verify",
        {
            "challenge_id": login.json()["challenge_id"],
            "code": totp_code_for(seeded["o1"], instant=clock.now()),
        },
    )
    before = HarnessAuditRecord.objects.count()
    response = api.post("/roles", {"name": "Librarian", "grants": []})
    assert response.status_code == 201
    assert HarnessAuditRecord.objects.count() == before + 1
    row = HarnessAuditRecord.objects.order_by("-occurred_at").first()
    assert row.action == "roles.created"
    assert "password" not in repr(row.after).lower()


def test_a_rejected_write_leaves_no_audit_row(api, seeded, clock):
    """A refused write must leave no trail of having partially happened."""
    from m01_helpers import totp_code_for

    from shared.harness.models import HarnessAuditRecord

    enrol_and_activate(api, seeded["o1"], "o1", clock)
    login = api.post("/auth/login", {"login_name": LOGINS["o1"], "password": PASSWORDS["o1"]})
    clock.advance(seconds=31)
    api.post(
        "/auth/2fa/verify",
        {
            "challenge_id": login.json()["challenge_id"],
            "code": totp_code_for(seeded["o1"], instant=clock.now()),
        },
    )
    before = HarnessAuditRecord.objects.count()
    bad = api.post(
        "/roles",
        {
            "name": "Bad",
            "grants": [
                {
                    "action": "roles.invent",
                    "scope_type": "school",
                    "scope_id": None,
                    "valid_from": "2026-06-01",
                    "valid_to": None,
                }
            ],
        },
    )
    assert bad.status_code == 422
    assert HarnessAuditRecord.objects.count() == before
