"""M01 acceptance: roles, escalation, last-owner, isolation, concurrency, rollback."""

from __future__ import annotations

import pytest
from m01_helpers import LOGINS, PASSWORDS, enrol_and_activate, totp_code_for

from shared import fixtures

pytestmark = [pytest.mark.django_db, pytest.mark.module]


def sign_in(api, label, seeded, clock):
    """Take an account all the way to a fresh two-factor session."""
    enrol_and_activate(api, seeded[label], label, clock)
    login = api.post("/auth/login", {"login_name": LOGINS[label], "password": PASSWORDS[label]})
    if login.json()["next_action"] == "totp_required":
        code = totp_code_for(seeded[label], instant=clock.now())
        response = api.post(
            "/auth/2fa/verify", {"challenge_id": login.json()["challenge_id"], "code": code}
        )
        assert response.status_code == 200, response.content
    return api


# --- the protected business endpoint --------------------------------------


def test_an_owner_with_fresh_two_factor_can_list_accounts(api, seeded, clock):
    sign_in(api, "o1", seeded, clock)
    response = api.get("/accounts")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "next_cursor"}
    # Only School A accounts. The School B owner must be invisible.
    logins = {item["login_name"] for item in body["items"]}
    assert LOGINS["o1"] in logins
    assert LOGINS["o2_school_b"] not in logins


def test_account_records_never_expose_credential_material(api, seeded, clock):
    sign_in(api, "o1", seeded, clock)
    body = api.get("/accounts").json()
    serialised = repr(body)
    for forbidden in ("password", "secret", "code_hash", "token", "encrypted"):
        assert forbidden not in serialised.lower(), forbidden
    # has_active_factor is a boolean only: an administrator never sees another
    # user's factor.
    assert all(isinstance(item["has_active_factor"], bool) for item in body["items"])


# --- two-school isolation -------------------------------------------------


def test_a_school_b_account_cannot_sign_in_to_a_school_a_deployment(api, seeded):
    """The school comes from deployment configuration, not from the request."""
    response = api.post(
        "/auth/login",
        {"login_name": LOGINS["o2_school_b"], "password": PASSWORDS["o2_school_b"]},
    )
    assert response.status_code == 401
    assert response.json()["message_key"] == "error.challenge_invalid"


def test_a_school_b_role_is_404_not_403(api, seeded, clock):
    """Acceptance: cross-school access is 404, never 403."""
    from modules.access.models import Role

    sign_in(api, "o1", seeded, clock)
    school_b_role = Role.objects.get(school_id=fixtures.SCHOOL_B)
    response = api.put(
        f"/roles/{school_b_role.id}/grants",
        {"name": "Hijacked", "grants": [], "expected_version": 1},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "object_inaccessible"


def test_a_client_cannot_assert_its_own_school(api, seeded, clock):
    sign_in(api, "o1", seeded, clock)
    response = api.get("/accounts", HTTP_X_SCHOOL_ID=str(fixtures.SCHOOL_B))
    assert response.status_code == 400
    assert response.json()["message_key"] == "error.client_asserted_identity"


# --- escalation and delegation -------------------------------------------


def test_a_teacher_cannot_create_a_role(api, seeded, clock):
    """Acceptance: no self-escalation. T1 holds only auth.factor.manage_self."""
    sign_in(api, "t1", seeded, clock)
    response = api.post(
        "/roles",
        {
            "name": "Escalated",
            "grants": [
                {
                    "action": "roles.manage",
                    "scope_type": "school",
                    "scope_id": None,
                    "valid_from": "2026-06-01",
                    "valid_to": None,
                }
            ],
        },
    )
    assert response.status_code == 403


def test_an_owner_cannot_grant_a_permission_it_does_not_hold(api, seeded, clock):
    """Escalation is checked against what the actor actually holds."""
    from modules.access.models import Grant, Role

    sign_in(api, "o1", seeded, clock)
    owner_role = Role.objects.get(school_id=fixtures.SCHOOL_A, is_owner_role=True)
    # Strip the owner's own roles.delegate, then try to delegate it.
    Grant.objects.filter(role=owner_role, action="roles.delegate").delete()

    response = api.post(
        "/roles",
        {
            "name": "Delegator",
            "grants": [
                {
                    "action": "roles.delegate",
                    "scope_type": "school",
                    "scope_id": None,
                    "valid_from": "2026-06-01",
                    "valid_to": None,
                }
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "error.grant_escalation"


def test_an_unknown_permission_is_refused(api, seeded, clock):
    sign_in(api, "o1", seeded, clock)
    response = api.post(
        "/roles",
        {
            "name": "Invented",
            "grants": [
                {
                    "action": "roles.invent_power",
                    "scope_type": "school",
                    "scope_id": None,
                    "valid_from": "2026-06-01",
                    "valid_to": None,
                }
            ],
        },
    )
    assert response.status_code == 422


# --- last-owner protection, versioning, unknown fields -------------------


def test_the_last_active_owner_is_protected(api, seeded, clock):
    """Acceptance: the change that would leave no owner is refused."""
    from modules.access.models import Role

    sign_in(api, "o1", seeded, clock)
    owner_role = Role.objects.get(school_id=fixtures.SCHOOL_A, is_owner_role=True)
    response = api.put(
        f"/roles/{owner_role.id}/grants",
        {
            "name": owner_role.name,
            "grants": [
                {
                    "action": "auth.factor.manage_self",
                    "scope_type": "self",
                    "scope_id": None,
                    "valid_from": "2026-06-01",
                    "valid_to": None,
                }
            ],
            "expected_version": owner_role.version,
        },
    )
    assert response.status_code == 409
    assert response.json()["message_key"] == "error.last_owner_protected"


def test_a_stale_expected_version_is_refused(api, seeded, clock):
    """Acceptance: stale edit is 409, never a silent overwrite."""
    from modules.access.models import Role

    sign_in(api, "o1", seeded, clock)
    role = Role.objects.get(school_id=fixtures.SCHOOL_A, name="Teacher")
    grants = [
        {
            "action": "auth.factor.manage_self",
            "scope_type": "self",
            "scope_id": None,
            "valid_from": "2026-06-01",
            "valid_to": None,
        }
    ]
    first = api.put(
        f"/roles/{role.id}/grants",
        {"name": role.name, "grants": grants, "expected_version": role.version},
    )
    assert first.status_code == 200
    assert first.json()["version"] == role.version + 1

    stale = api.put(
        f"/roles/{role.id}/grants",
        {"name": role.name, "grants": grants, "expected_version": role.version},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "version_conflict"


def test_a_missing_expected_version_is_refused_not_treated_as_overwrite(api, seeded, clock):
    from modules.access.models import Role

    sign_in(api, "o1", seeded, clock)
    role = Role.objects.get(school_id=fixtures.SCHOOL_A, name="Teacher")
    response = api.put(f"/roles/{role.id}/grants", {"name": role.name, "grants": []})
    assert response.status_code == 422


def test_an_unknown_write_field_is_refused(api, seeded, clock):
    """Acceptance: reject unknown write fields."""
    sign_in(api, "o1", seeded, clock)
    response = api.post("/roles", {"name": "Fine", "grants": [], "sneaky_extra_field": True})
    assert response.status_code == 422
    assert response.json()["message_key"] == "error.unknown_field"
    assert response.json()["field_errors"][0]["field"] == "sneaky_extra_field"


def test_a_grant_change_emits_an_event_and_bumps_the_policy_version(api, seeded, clock):
    from modules.access.models import PolicyVersion, Role
    from shared.harness.models import HarnessOutboxEvent

    sign_in(api, "o1", seeded, clock)
    role = Role.objects.get(school_id=fixtures.SCHOOL_A, name="Guardian")
    api.put(
        f"/roles/{role.id}/grants",
        {"name": role.name, "grants": [], "expected_version": role.version},
    )
    events = HarnessOutboxEvent.objects.filter(event_type="RoleGrantsChanged.v1")
    assert events.count() == 1
    payload = events.first().payload
    assert "policy_version" in payload
    assert PolicyVersion.objects.get(school_id=fixtures.SCHOOL_A).version >= 2
    # No credential material in an event payload, ever.
    assert "password" not in repr(payload).lower()


# --- sessions --------------------------------------------------------------


def test_a_caller_sees_only_their_own_sessions(api, seeded, clock):
    from modules.access.models import Session

    sign_in(api, "o1", seeded, clock)
    # Give another account a live session too.
    other = api.__class__()
    sign_in(other, "p1", seeded, clock)

    body = api.get("/sessions").json()
    own_ids = {str(row.id) for row in Session.objects.filter(user_id=seeded["o1"].id)}
    returned = {item["id"] for item in body["items"]}
    assert returned <= own_ids
    assert any(item["is_current"] for item in body["items"])


def test_revoking_another_users_session_is_404(api, seeded, clock):
    from modules.access.models import Session

    other = api.__class__()
    sign_in(other, "p1", seeded, clock)
    foreign = Session.objects.filter(user_id=seeded["p1"].id, revoked_at__isnull=True).first()

    sign_in(api, "o1", seeded, clock)
    response = api.post(f"/sessions/{foreign.id}/revoke")
    assert response.status_code == 404


def test_logout_revokes_the_session_and_clears_the_cookie(api, seeded, clock):
    sign_in(api, "o1", seeded, clock)
    assert api.get("/accounts").status_code == 200
    assert api.post("/auth/logout").status_code == 200
    assert api.get("/accounts").status_code == 401


# --- csrf ------------------------------------------------------------------


def test_a_cookie_authenticated_write_without_the_csrf_header_is_refused(api, seeded, clock):
    sign_in(api, "o1", seeded, clock)
    # Post without echoing the CSRF cookie into the header.
    response = api.client.post(
        "/api/v1/roles",
        data={"name": "NoCsrf", "grants": []},
        content_type="application/json",
    )
    assert response.status_code == 422
    assert response.json()["message_key"] == "error.csrf_failed"
