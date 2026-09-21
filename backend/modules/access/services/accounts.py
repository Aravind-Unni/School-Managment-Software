"""Account lifecycle: create, assign roles, reset password, (de)activate.

Rules this file keeps:
  * An account that acts as a Registry person carries that person's id as its
    own id. Every module compares ``RequestContext.actor_id`` against Registry
    person ids (assigned teacher, guardian link), so the two must be one value.
  * A caller can only hand out roles whose grants they hold themselves (the
    same escalation rule as role editing), and only an owner can make an owner.
  * The last active owner can never be deactivated or stripped of the role.
  * Password changes and deactivation revoke every live session of the account.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime

from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction

from contracts.errors import (
    FieldError,
    ObjectInaccessible,
    StateConflict,
    ValidationFailed,
    VersionConflict,
)

from ..scopes import ScopeType
from .policy import GrantFact
from .roles import GrantInput, assert_no_escalation
from .sessions import revoke_all_for_user

#: Minimum length for any password set through this service.
MINIMUM_PASSWORD_LENGTH = 10

#: Alphabet for generated temporary passwords: no 0/O/1/l/I confusion, because
#: an administrator reads these aloud or writes them on a slip for a parent.
TEMPORARY_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
TEMPORARY_PASSWORD_LENGTH = 12


@dataclass(frozen=True, slots=True)
class CreatedAccount:
    """A new account plus its one-time temporary password, when generated."""

    user: object
    temporary_password: str | None


def generate_temporary_password() -> str:
    """Return a random readable password. Shown once; never stored in clear."""
    return "".join(
        secrets.choice(TEMPORARY_PASSWORD_ALPHABET) for _ in range(TEMPORARY_PASSWORD_LENGTH)
    )


def validate_password_strength(password: str, *, field: str = "password") -> None:
    """Refuse a password that is too short or blank. Does not check breach lists."""
    if len(password or "") < MINIMUM_PASSWORD_LENGTH or not password.strip():
        raise ValidationFailed(
            "error.validation_failed",
            field_errors=(FieldError(field, "error.password_too_short"),),
        )


def _load_roles(school_id: uuid.UUID, role_ids: tuple[uuid.UUID, ...]):
    """Return the named roles of this school, or raise when any is absent."""
    from ..models import Role

    unique_ids = tuple(dict.fromkeys(role_ids))
    roles = list(Role.objects.filter(school_id=school_id, id__in=unique_ids))
    if len(roles) != len(unique_ids):
        raise ValidationFailed(
            "error.validation_failed",
            field_errors=(FieldError("role_ids", "error.unknown_role"),),
        )
    return roles


def _assert_may_hand_out(
    roles, *, actor_is_owner: bool, held: tuple[GrantFact, ...], effective_date: date
) -> None:
    """Refuse roles the caller could not have granted themselves."""
    from ..models import Grant

    if any(role.is_owner_role for role in roles) and not actor_is_owner:
        raise ValidationFailed(
            "error.grant_escalation",
            field_errors=(FieldError("role_ids", "error.grant_escalation"),),
        )
    requested = tuple(
        GrantInput(
            action=row.action,
            scope_type=ScopeType(row.scope_type),
            scope_id=row.scope_id,
            valid_from=effective_date,
            valid_to=row.valid_to,
        )
        for row in Grant.objects.filter(role__in=[role.id for role in roles])
    )
    if not actor_is_owner:
        assert_no_escalation(requested=requested, held=held, effective_date=effective_date)


def actor_is_owner(school_id: uuid.UUID, actor_id: uuid.UUID) -> bool:
    """Return whether the actor holds an owner role in this school."""
    from ..models import UserRole

    return UserRole.objects.filter(
        school_id=school_id, user_id=actor_id, role__is_owner_role=True, user__active=True
    ).exists()


def _active_owner_count(school_id: uuid.UUID) -> int:
    """Return how many active accounts hold an owner role."""
    from ..models import UserRole

    return (
        UserRole.objects.filter(
            school_id=school_id, role__is_owner_role=True, user__active=True
        )
        .values("user_id")
        .distinct()
        .count()
    )


def create_account(
    *,
    school_id: uuid.UUID,
    login_name: str,
    display_name: str,
    person_id: uuid.UUID | None,
    role_ids: tuple[uuid.UUID, ...],
    password: str | None,
    actor_id: uuid.UUID,
    held: tuple[GrantFact, ...],
    effective_date: date,
    instant: datetime,
) -> CreatedAccount:
    """Create an account, optionally linked to a Registry person, with roles.

    When ``password`` is None a temporary one is generated and returned once.
    Assumes the caller already passed ``accounts.manage``. Does not verify the
    person exists in Registry; the caller does that through RegistryPort.
    """
    from ..models import User, UserRole

    login_name = (login_name or "").strip().lower()
    display_name = (display_name or "").strip()
    problems: list[FieldError] = []
    if not login_name or len(login_name) > 150 or any(c.isspace() for c in login_name):
        problems.append(FieldError("login_name", "error.invalid_login_name"))
    if not display_name:
        problems.append(FieldError("display_name", "error.required"))
    if problems:
        raise ValidationFailed("error.validation_failed", field_errors=tuple(problems))

    temporary = None
    if password is None:
        temporary = generate_temporary_password()
        password = temporary
    else:
        validate_password_strength(password)

    roles = _load_roles(school_id, role_ids)
    _assert_may_hand_out(
        roles,
        actor_is_owner=actor_is_owner(school_id, actor_id),
        held=held,
        effective_date=effective_date,
    )

    account_id = person_id or uuid.uuid4()
    if User.objects.filter(id=account_id).exists():
        raise StateConflict("error.person_already_has_account")
    try:
        with transaction.atomic():
            user = User.objects.create(
                id=account_id,
                school_id=school_id,
                login_name=login_name,
                password_hash=make_password(password),
                display_name=display_name,
                person_id=person_id,
                active=True,
                version=1,
                created_at=instant,
                updated_at=instant,
            )
            UserRole.objects.bulk_create(
                [
                    UserRole(school_id=school_id, user=user, role=role, granted_at=instant)
                    for role in roles
                ]
            )
    except IntegrityError as exc:
        raise ValidationFailed(
            "error.validation_failed",
            field_errors=(FieldError("login_name", "error.login_name_taken"),),
        ) from exc
    return CreatedAccount(user=user, temporary_password=temporary)


def _load_account_for_update(school_id: uuid.UUID, account_id, expected_version: int):
    """Return the account row locked for update, checking its version."""
    from ..models import User

    user = User.objects.select_for_update().filter(id=account_id, school_id=school_id).first()
    if user is None:
        raise ObjectInaccessible("error.object_inaccessible")
    if user.version != expected_version:
        raise VersionConflict(expected_version=expected_version, actual_version=user.version)
    return user


def replace_roles(
    *,
    school_id: uuid.UUID,
    account_id,
    role_ids: tuple[uuid.UUID, ...],
    expected_version: int,
    actor_id: uuid.UUID,
    held: tuple[GrantFact, ...],
    effective_date: date,
    instant: datetime,
):
    """Replace an account's role set. Refuses removing the last owner."""
    from ..models import UserRole

    roles = _load_roles(school_id, role_ids)
    owner = actor_is_owner(school_id, actor_id)
    _assert_may_hand_out(roles, actor_is_owner=owner, held=held, effective_date=effective_date)
    with transaction.atomic():
        user = _load_account_for_update(school_id, account_id, expected_version)
        currently_owner = UserRole.objects.filter(user=user, role__is_owner_role=True).exists()
        stays_owner = any(role.is_owner_role for role in roles)
        if currently_owner and not stays_owner:
            if not owner:
                raise ValidationFailed("error.grant_escalation")
            if user.active and _active_owner_count(school_id) <= 1:
                raise StateConflict("error.last_owner")
        UserRole.objects.filter(user=user).delete()
        UserRole.objects.bulk_create(
            [
                UserRole(school_id=school_id, user=user, role=role, granted_at=instant)
                for role in roles
            ]
        )
        user.version += 1
        user.updated_at = instant
        user.save(update_fields=["version", "updated_at"])
        revoke_all_for_user(user, instant=instant)
    return user


def set_active(
    *,
    school_id: uuid.UUID,
    account_id,
    active: bool,
    expected_version: int,
    actor_id: uuid.UUID,
    instant: datetime,
):
    """Activate or deactivate an account. Refuses self and the last owner."""
    from ..models import UserRole

    if str(account_id) == str(actor_id) and not active:
        raise StateConflict("error.cannot_deactivate_self")
    with transaction.atomic():
        user = _load_account_for_update(school_id, account_id, expected_version)
        is_owner = UserRole.objects.filter(user=user, role__is_owner_role=True).exists()
        if is_owner and not actor_is_owner(school_id, actor_id):
            raise ValidationFailed("error.grant_escalation")
        if not active and is_owner and user.active and _active_owner_count(school_id) <= 1:
            raise StateConflict("error.last_owner")
        user.active = active
        user.version += 1
        user.updated_at = instant
        user.save(update_fields=["active", "version", "updated_at"])
        if not active:
            revoke_all_for_user(user, instant=instant)
    return user


def reset_password(
    *, school_id: uuid.UUID, account_id, actor_id: uuid.UUID, instant: datetime
) -> tuple[object, str]:
    """Set a new temporary password and sign the account out everywhere.

    Only an owner may reset an owner's password. Returns (user, temporary).
    Does not reset the second factor; that is the lost-device flow.
    """
    from ..models import User, UserRole

    with transaction.atomic():
        user = (
            User.objects.select_for_update().filter(id=account_id, school_id=school_id).first()
        )
        if user is None:
            raise ObjectInaccessible("error.object_inaccessible")
        target_is_owner = UserRole.objects.filter(user=user, role__is_owner_role=True).exists()
        if target_is_owner and not actor_is_owner(school_id, actor_id):
            raise ValidationFailed("error.grant_escalation")
        temporary = generate_temporary_password()
        user.password_hash = make_password(temporary)
        user.version += 1
        user.updated_at = instant
        user.save(update_fields=["password_hash", "version", "updated_at"])
        revoke_all_for_user(user, instant=instant)
    return user, temporary


def change_own_password(
    *, user, current_password: str, new_password: str, keep_session_id, instant: datetime
) -> None:
    """Change one's own password after proving the current one.

    Revokes every other session of the account; the current one stays.
    """
    if not check_password(current_password or "", user.password_hash):
        raise ValidationFailed(
            "error.validation_failed",
            field_errors=(FieldError("current_password", "error.password_incorrect"),),
        )
    validate_password_strength(new_password, field="new_password")
    if new_password == current_password:
        raise ValidationFailed(
            "error.validation_failed",
            field_errors=(FieldError("new_password", "error.password_unchanged"),),
        )
    user.password_hash = make_password(new_password)
    user.password_confirmed_at = instant
    user.version += 1
    user.updated_at = instant
    user.save(update_fields=["password_hash", "password_confirmed_at", "version", "updated_at"])
    revoke_all_for_user(user, instant=instant, except_session_id=keep_session_id)
