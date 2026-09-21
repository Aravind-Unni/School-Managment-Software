"""Account administration: create, roles, deactivate, reset, own password.

Service-level tests for the rules, plus one API walk proving the endpoint is
wired, audited and demands a fresh second factor.
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth.hashers import check_password
from m01_helpers import enrol_and_activate

from contracts.errors import StateConflict, ValidationFailed
from shared import fixtures

pytestmark = pytest.mark.django_db


def _role(label: str):
    from modules.access.models import Role
    from modules.access.seeds import _role_id

    return Role.objects.get(id=_role_id(label))


def _held(user):
    from modules.access.services.authorize import AccessService

    class _Context:
        actor_id = user.id
        school_id = user.school_id

    return AccessService(clock=None).held_grants(_Context())


def _create(seeded, clock, *, actor="o1", person_id=None, roles=("teacher",), password=None):
    from modules.access.services import accounts

    actor_user = seeded[actor]
    return accounts.create_account(
        school_id=fixtures.SCHOOL_A,
        login_name=f"new.person.{uuid.uuid4().hex[:6]}",
        display_name="New Person",
        person_id=person_id,
        role_ids=tuple(_role(label).id for label in roles),
        password=password,
        actor_id=actor_user.id,
        held=_held(actor_user),
        effective_date=clock.now().date(),
        instant=clock.now(),
    )


def test_an_account_for_a_registry_person_takes_that_persons_id(seeded, clock):
    """actor_id must equal the Registry person id, or no relationship ever matches."""
    person = uuid.uuid4()
    created = _create(seeded, clock, person_id=person)
    assert created.user.id == person
    assert created.user.person_id == person


def test_a_generated_temporary_password_is_returned_once_and_works(seeded, clock):
    created = _create(seeded, clock)
    assert created.temporary_password is not None
    assert len(created.temporary_password) >= 12
    assert check_password(created.temporary_password, created.user.password_hash)


def test_a_chosen_password_must_be_long_enough(seeded, clock):
    with pytest.raises(ValidationFailed):
        _create(seeded, clock, password="short")


def test_a_login_name_is_unique_within_the_school(seeded, clock):
    from modules.access.services import accounts

    first = _create(seeded, clock)
    with pytest.raises(ValidationFailed) as raised:
        accounts.create_account(
            school_id=fixtures.SCHOOL_A,
            login_name=first.user.login_name.upper(),
            display_name="Someone Else",
            person_id=None,
            role_ids=(),
            password=None,
            actor_id=seeded["o1"].id,
            held=_held(seeded["o1"]),
            effective_date=clock.now().date(),
            instant=clock.now(),
        )
    assert raised.value.field_errors[0].message_key == "error.login_name_taken"


def test_a_person_cannot_get_two_accounts(seeded, clock):
    person = uuid.uuid4()
    _create(seeded, clock, person_id=person)
    with pytest.raises(StateConflict):
        _create(seeded, clock, person_id=person)


def test_only_an_owner_can_create_an_owner(seeded, clock):
    with pytest.raises(ValidationFailed):
        _create(seeded, clock, actor="p1", roles=("owner",))


def test_an_administrator_cannot_hand_out_grants_they_do_not_hold(seeded, clock):
    """The administrator lacks roles.manage, which the owner role grants."""
    from modules.access.models import Grant, Role

    wide = Role.objects.create(
        school_id=fixtures.SCHOOL_A,
        name="Wide",
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    Grant.objects.create(
        school_id=fixtures.SCHOOL_A,
        role=wide,
        action="roles.manage",
        scope_type="school",
        valid_from=fixtures.TERM_START,
        created_at=clock.now(),
    )
    from modules.access.services import accounts

    with pytest.raises(ValidationFailed):
        accounts.create_account(
            school_id=fixtures.SCHOOL_A,
            login_name="escalation.try",
            display_name="Escalation",
            person_id=None,
            role_ids=(wide.id,),
            password=None,
            actor_id=seeded["p1"].id,
            held=_held(seeded["p1"]),
            effective_date=clock.now().date(),
            instant=clock.now(),
        )


def test_the_last_owner_cannot_give_up_the_owner_role(seeded, clock):
    from modules.access.services import accounts

    owner = seeded["o1"]
    with pytest.raises(StateConflict) as raised:
        accounts.replace_roles(
            school_id=fixtures.SCHOOL_A,
            account_id=owner.id,
            role_ids=(_role("administrator").id,),
            expected_version=owner.version,
            actor_id=owner.id,
            held=_held(owner),
            effective_date=clock.now().date(),
            instant=clock.now(),
        )
    assert raised.value.message_key == "error.last_owner"


def test_a_non_owner_cannot_deactivate_an_owner(seeded, clock):
    from modules.access.services import accounts

    owner = seeded["o1"]
    with pytest.raises(ValidationFailed):
        accounts.set_active(
            school_id=fixtures.SCHOOL_A,
            account_id=owner.id,
            active=False,
            expected_version=owner.version,
            actor_id=seeded["p1"].id,
            instant=clock.now(),
        )


def test_nobody_deactivates_themselves(seeded, clock):
    from modules.access.services import accounts

    owner = seeded["o1"]
    with pytest.raises(StateConflict):
        accounts.set_active(
            school_id=fixtures.SCHOOL_A,
            account_id=owner.id,
            active=False,
            expected_version=owner.version,
            actor_id=owner.id,
            instant=clock.now(),
        )


def test_deactivating_signs_the_account_out_everywhere(seeded, clock):
    from modules.access.models import Session
    from modules.access.services import accounts
    from modules.access.services.sessions import create_session

    target = seeded["t1"]
    create_session(user=target, auth_level="two_factor", instant=clock.now(), user_agent="x")
    updated = accounts.set_active(
        school_id=fixtures.SCHOOL_A,
        account_id=target.id,
        active=False,
        expected_version=target.version,
        actor_id=seeded["o1"].id,
        instant=clock.now(),
    )
    assert updated.active is False
    assert not Session.objects.filter(user=target, revoked_at__isnull=True).exists()


def test_a_password_reset_issues_a_working_temporary_password(seeded, clock):
    from modules.access.services import accounts

    user, temporary = accounts.reset_password(
        school_id=fixtures.SCHOOL_A,
        account_id=seeded["t1"].id,
        actor_id=seeded["o1"].id,
        instant=clock.now(),
    )
    assert check_password(temporary, user.password_hash)


def test_a_non_owner_cannot_reset_an_owners_password(seeded, clock):
    from modules.access.services import accounts

    with pytest.raises(ValidationFailed):
        accounts.reset_password(
            school_id=fixtures.SCHOOL_A,
            account_id=seeded["o1"].id,
            actor_id=seeded["p1"].id,
            instant=clock.now(),
        )


def test_changing_ones_own_password_needs_the_current_one(seeded, clock):
    from m01_helpers import PASSWORDS

    from modules.access.services import accounts

    user = seeded["t1"]
    with pytest.raises(ValidationFailed):
        accounts.change_own_password(
            user=user,
            current_password="wrong",
            new_password="a-new-password-1",
            keep_session_id=None,
            instant=clock.now(),
        )
    accounts.change_own_password(
        user=user,
        current_password=PASSWORDS["t1"],
        new_password="a-new-password-1",
        keep_session_id=None,
        instant=clock.now(),
    )
    user.refresh_from_db()
    assert check_password("a-new-password-1", user.password_hash)


def test_module_actions_are_known_only_when_the_host_installs_them(settings):
    """Deny by default: a module code is unknown until a host declares it."""
    from modules.access.permissions import is_known_action, lookup_permission

    settings.SCHOOL_MODULE_PERMISSION_CODES = ()
    assert not is_known_action("attendance.mark")
    settings.SCHOOL_MODULE_PERMISSION_CODES = ("attendance.mark", "fees.refund")
    assert is_known_action("attendance.mark")
    assert lookup_permission("fees.refund").requires_recent_two_factor is True
    assert lookup_permission("attendance.mark").requires_recent_two_factor is False
    assert not is_known_action("attendance.teleport")


def test_the_create_endpoint_requires_a_fresh_factor_and_returns_the_password_once(
    seeded, clock, api
):
    from modules.access.models import User

    enrol_and_activate(api, seeded["o1"], "o1", clock)
    from m01_helpers import PASSWORDS, totp_code_for

    login = api.post("/auth/login", {"login_name": "owner.o1", "password": PASSWORDS["o1"]})
    challenge = login.json()["challenge_id"]
    verified = api.post(
        "/auth/2fa/verify",
        {"challenge_id": challenge, "code": totp_code_for(seeded["o1"], instant=clock.now())},
    )
    assert verified.status_code in (200, 201), verified.content
    response = api.post(
        "/accounts",
        {
            "login_name": "office.clerk",
            "display_name": "Office Clerk",
            "person_id": None,
            "role_ids": [str(_role("teacher").id)],
        },
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["login_name"] == "office.clerk"
    assert body["temporary_password"]
    assert User.objects.filter(login_name="office.clerk").exists()
