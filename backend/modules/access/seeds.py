"""Synthetic seed scenarios for M01.

Every value is synthetic and derived from ``shared.fixtures``, so a scenario produces
identical rows on every machine. The passwords are test-only strings that exist
nowhere else; the accounts describe no real person.

Recorded in ``contracts/M01/fixtures/personas.json``, and a test asserts the two
agree so the documented cast cannot drift from what the seed actually creates.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.db import transaction

from shared import fixtures

from .models import (
    Grant,
    LoginChallenge,
    Permission,
    RecoveryCase,
    RecoveryCode,
    Role,
    User,
    UserRole,
)
from .models.accounts import CaseState
from .permissions import CATALOGUE
from .scopes import ScopeType
from .services.crypto import hash_recovery_code

#: Fixed instant inside the fixture term, so seeded rows are deterministic.
SEED_INSTANT = datetime(2026, 7, 15, 4, 30, tzinfo=UTC)
TERM_START = fixtures.TERM_START

#: Namespace for M01's seeded ids, so re-running a scenario is idempotent.
SEED_NAMESPACE = uuid.UUID("9f2c6a71-4d3b-4e5f-8a1c-0b7d6e5f4c3b")

#: The one recovery code that is already spent, so a replay can be tested without
#: first consuming a live one.
USED_RECOVERY_CODE = "USED1-CODE1"


def _id(label: str) -> uuid.UUID:
    """Return the deterministic id for a seeded row."""
    return uuid.uuid5(SEED_NAMESPACE, label)


def _account_id(label: str) -> uuid.UUID:
    """Return the id recorded in contracts/M01/fixtures/personas.json."""
    return fixtures.fixture_uuid(f"m01.account.{label}")


def _role_id(label: str) -> uuid.UUID:
    """Return the role id recorded in the fixture file."""
    return fixtures.fixture_uuid(f"m01.role.{label}")


#: login label -> (login_name, password, display, roles, person_id, school)
ACCOUNTS: tuple[
    tuple[str, str, str, str, tuple[str, ...], uuid.UUID | None, uuid.UUID], ...
] = (
    (
        "o1",
        "owner.o1",
        "Owner-O1-test-only",
        "O1 Owner (synthetic)",
        ("owner",),
        None,
        fixtures.SCHOOL_A,
    ),
    (
        "t1",
        "teacher.t1",
        "Teacher-T1-test-only",
        "T1 Teacher (synthetic)",
        ("teacher",),
        fixtures.TEACHER_T1,
        fixtures.SCHOOL_A,
    ),
    (
        "g1",
        "guardian.g1",
        "Guardian-G1-test-only",
        "G1 Guardian (synthetic)",
        ("guardian",),
        fixtures.GUARDIAN_G1,
        fixtures.SCHOOL_A,
    ),
    (
        "p1",
        "principal.p1",
        "Principal-P1-test-only",
        "P1 Principal (synthetic)",
        ("administrator",),
        fixtures.PRINCIPAL_P1,
        fixtures.SCHOOL_A,
    ),
    (
        "o2_school_b",
        "owner.o2",
        "Owner-O2-test-only",
        "O2 Owner at School B (synthetic)",
        ("owner_b",),
        None,
        fixtures.SCHOOL_B,
    ),
)

#: role label -> (name, is_owner, requires_2fa, school, granted actions)
ROLES: tuple[tuple[str, str, bool, bool, uuid.UUID, tuple[str, ...]], ...] = (
    (
        "owner",
        "Owner",
        True,
        True,
        fixtures.SCHOOL_A,
        (
            "roles.manage",
            "roles.delegate",
            "accounts.manage",
            "auth.factor.manage_self",
            "auth.factor.reset_other",
        ),
    ),
    (
        "administrator",
        "Administrator",
        False,
        True,
        fixtures.SCHOOL_A,
        ("accounts.manage", "auth.factor.manage_self", "auth.factor.reset_other"),
    ),
    ("teacher", "Teacher", False, True, fixtures.SCHOOL_A, ("auth.factor.manage_self",)),
    ("guardian", "Guardian", False, False, fixtures.SCHOOL_A, ("auth.factor.manage_self",)),
    (
        "owner_b",
        "Owner",
        True,
        True,
        fixtures.SCHOOL_B,
        ("roles.manage", "accounts.manage", "auth.factor.manage_self"),
    ),
)

#: Actions granted at SELF scope rather than school-wide.
SELF_SCOPED_ACTIONS = frozenset({"auth.factor.manage_self"})


def _ensure_permissions() -> None:
    """Load the closed permission catalogue into the database."""
    for spec in CATALOGUE:
        Permission.objects.update_or_create(
            code=spec.code,
            defaults={
                "description": spec.description,
                "requires_recent_two_factor": spec.requires_recent_two_factor,
            },
        )


def _ensure_roles() -> dict[str, Role]:
    """Create the fixture roles and their grants idempotently."""
    created: dict[str, Role] = {}
    for label, name, is_owner, needs_2fa, school, actions in ROLES:
        role, _ = Role.objects.update_or_create(
            id=_role_id(label),
            defaults={
                "school_id": school,
                "name": name,
                "is_owner_role": is_owner,
                "requires_two_factor": needs_2fa,
                "created_at": SEED_INSTANT,
                "updated_at": SEED_INSTANT,
            },
        )
        Grant.objects.filter(role=role).delete()
        Grant.objects.bulk_create(
            [
                Grant(
                    id=_id(f"grant.{label}.{action}"),
                    school_id=school,
                    role=role,
                    action=action,
                    scope_type=(
                        ScopeType.SELF.value
                        if action in SELF_SCOPED_ACTIONS
                        else ScopeType.SCHOOL.value
                    ),
                    scope_id=None,
                    valid_from=TERM_START,
                    valid_to=None,
                    created_at=SEED_INSTANT,
                )
                for action in actions
            ]
        )
        created[label] = role
    return created


def _ensure_accounts(roles: dict[str, Role]) -> dict[str, User]:
    """Create the fixture accounts idempotently."""
    created: dict[str, User] = {}
    for label, login_name, password, display, role_labels, person_id, school in ACCOUNTS:
        user, _ = User.objects.update_or_create(
            id=_account_id(label),
            defaults={
                "school_id": school,
                "login_name": login_name,
                "password_hash": make_password(password),
                "display_name": display,
                "person_id": person_id,
                "active": True,
                "version": 1,
                "created_at": SEED_INSTANT,
                "updated_at": SEED_INSTANT,
            },
        )
        UserRole.objects.filter(user=user).delete()
        UserRole.objects.bulk_create(
            [
                UserRole(
                    id=_id(f"userrole.{label}.{role_label}"),
                    school_id=school,
                    user=user,
                    role=roles[role_label],
                    granted_at=SEED_INSTANT,
                )
                for role_label in role_labels
            ]
        )
        created[label] = user
    return created


def baseline() -> dict[str, int]:
    """Seed the full cast plus the preloaded edge-case state.

    Includes an ALREADY-EXPIRED challenge and an ALREADY-USED recovery code, so those
    paths are testable without waiting five minutes or spending a live code. Also a
    pending lost-device case for T1, awaiting P1's approval, which is the device-loss
    recovery path with no SMS service anywhere.
    """
    with transaction.atomic():
        _ensure_permissions()
        roles = _ensure_roles()
        users = _ensure_accounts(roles)

        # An expired challenge for G1.
        LoginChallenge.objects.update_or_create(
            id=fixtures.fixture_uuid("m01.challenge.expired"),
            defaults={
                "school_id": fixtures.SCHOOL_A,
                "user": users["g1"],
                "created_at": SEED_INSTANT - timedelta(minutes=30),
                "expires_at": SEED_INSTANT - timedelta(minutes=25),
                "attempts": 0,
            },
        )

        # A spent recovery code for G1.
        RecoveryCode.objects.update_or_create(
            id=_id("recovery.used"),
            defaults={
                "school_id": fixtures.SCHOOL_A,
                "user": users["g1"],
                "code_hash": hash_recovery_code(
                    USED_RECOVERY_CODE, school_id=fixtures.SCHOOL_A
                ),
                "created_at": SEED_INSTANT - timedelta(days=1),
                "used_at": SEED_INSTANT - timedelta(hours=1),
            },
        )

        # A pending lost-device case for T1.
        RecoveryCase.objects.update_or_create(
            id=fixtures.fixture_uuid("m01.case.t1_lost_device"),
            defaults={
                "school_id": fixtures.SCHOOL_A,
                "user": users["t1"],
                "reason": "Synthetic: T1 reports the authenticator device was lost.",
                "state": CaseState.PENDING,
                "created_at": SEED_INSTANT,
                "version": 1,
            },
        )

    return {
        "accounts": User.objects.count(),
        "roles": Role.objects.count(),
        "grants": Grant.objects.count(),
        "permissions": Permission.objects.count(),
        "expired_challenges": LoginChallenge.objects.filter(
            expires_at__lt=SEED_INSTANT
        ).count(),
        "used_recovery_codes": RecoveryCode.objects.filter(used_at__isnull=False).count(),
        "pending_cases": RecoveryCase.objects.filter(state=CaseState.PENDING).count(),
    }


def empty() -> dict[str, int]:
    """Remove all M01 rows, for empty-state UI and migration-on-empty tests."""
    with transaction.atomic():
        for model in (
            RecoveryCase,
            RecoveryCode,
            LoginChallenge,
            Grant,
            UserRole,
            Role,
            User,
        ):
            model.objects.all().delete()
    return {"accounts": 0, "roles": 0}


#: Scenario name -> loader. Must match dev/modules/M01/module.json.
SCENARIOS = {"baseline": baseline, "empty": empty}
