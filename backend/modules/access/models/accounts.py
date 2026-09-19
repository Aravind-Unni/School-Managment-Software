"""Accounts, roles, permissions and grants.

Every row carries a trusted ``school_id`` taken from the RequestContext, never
from a request body. Mutable aggregates carry an integer ``version`` compared
against ``expected_version`` on write.

Does not handle: authentication. That is ``models/auth.py``.
"""

from __future__ import annotations

import enum
import uuid

from django.db import models

from ..scopes import SCOPE_TYPE_CHOICES


class User(models.Model):
    """One login account, scoped to exactly one school.

    ``login_name`` is unique PER SCHOOL, not globally: two schools may both have
    a "principal", and a global unique constraint would leak the existence of
    accounts across tenants.

    ``password_hash`` uses Django's configured hasher. The plaintext is never
    stored, never logged and never returned.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    login_name = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=256)
    display_name = models.CharField(max_length=200)
    #: Optional link to the Registry person this account acts as. Nullable
    #: because a service or owner account need not be a school person.
    person_id = models.UUIDField(null=True, blank=True, db_index=True)
    active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    #: When the password was last confirmed interactively. Factor enrolment and
    #: replacement require a RECENT confirmation, so this is not merely audit.
    password_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "access_user"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "login_name"], name="access_user_unique_login_per_school"
            )
        ]
        indexes = [models.Index(fields=["school_id", "active"])]

    def __str__(self) -> str:
        """Return a short identifier. Never includes credential material."""
        return f"User {self.login_name}@{self.school_id}"


class Role(models.Model):
    """A named bundle of grants within one school.

    ``is_owner_role`` marks the protected role: the last account holding it
    cannot lose it, and its required second factor cannot be disabled. There is
    deliberately no hard-coded privileged login name -- ownership is a role, so a
    school can rename or re-seat it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=100)
    is_owner_role = models.BooleanField(default=False)
    requires_two_factor = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "access_role"
        constraints = [
            models.UniqueConstraint(
                fields=["school_id", "name"], name="access_role_unique_name_per_school"
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"Role {self.name}@{self.school_id}"


class Permission(models.Model):
    """One action code the system knows about.

    The catalogue is closed: an action absent from this table is denied by
    default rather than treated as unrestricted. Codes are globally unique
    because they name platform-wide actions, not per-school ones.
    """

    code = models.CharField(max_length=128, primary_key=True)
    description = models.CharField(max_length=300)
    #: True when the action is sensitive enough to demand a recently asserted
    #: second factor, independent of which role holds it.
    requires_recent_two_factor = models.BooleanField(default=False)

    class Meta:
        db_table = "access_permission"

    def __str__(self) -> str:
        """Return the code."""
        return self.code


class UserRole(models.Model):
    """Membership of an account in a role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_links")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_links")
    granted_at = models.DateTimeField()

    class Meta:
        db_table = "access_user_role"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="access_user_role_unique")
        ]

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"{self.user_id} in {self.role_id}"


class Grant(models.Model):
    """One permission granted to a role OR directly to a user, within a scope.

    Exactly one of ``role`` and ``user`` is set -- enforced by a database
    constraint, because a grant attached to both would be ambiguous about whose
    removal revokes it.

    ``valid_from``/``valid_to`` are school-local dates (Asia/Kolkata), inclusive.
    A grant outside its window does not authorise, which is how a temporary
    delegation expires without anyone remembering to remove it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    role = models.ForeignKey(
        Role, null=True, blank=True, on_delete=models.CASCADE, related_name="grants"
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="direct_grants"
    )
    action = models.CharField(max_length=128, db_index=True)
    scope_type = models.CharField(max_length=16, choices=SCOPE_TYPE_CHOICES)
    scope_id = models.UUIDField(null=True, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "access_grant"
        indexes = [
            models.Index(fields=["school_id", "action"]),
            models.Index(fields=["role", "action"]),
            models.Index(fields=["user", "action"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(role__isnull=False, user__isnull=True)
                    | models.Q(role__isnull=True, user__isnull=False)
                ),
                name="access_grant_exactly_one_holder",
            ),
            # A school-wide or self grant must not name a scope object; a
            # section/subject grant must. Enforced in the database so a bad row
            # cannot exist even if a service forgets.
            models.CheckConstraint(
                condition=(
                    models.Q(scope_type__in=["school", "self"], scope_id__isnull=True)
                    | models.Q(scope_type__in=["section", "subject"], scope_id__isnull=False)
                ),
                name="access_grant_scope_id_matches_type",
            ),
        ]

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"Grant {self.action} ({self.scope_type})"


class AuthLevelChoices(models.TextChoices):
    """How strongly a session's holder proved identity.

    ``RECOVERY`` is deliberately its own level, weaker than PASSWORD_TOTP: a
    recovery session may re-enrol a factor and nothing else, so it must never
    satisfy a business permission check.
    """

    PASSWORD = "password", "Password only"
    PASSWORD_TOTP = "password_totp", "Password and TOTP"
    RECOVERY = "recovery", "Recovery code"


class FactorState(enum.StrEnum):
    """Lifecycle of a TOTP factor."""

    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class CaseState(enum.StrEnum):
    """Lifecycle of a lost-device identity-verification case."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PolicyVersion(models.Model):
    """A per-school counter bumped whenever grants change.

    M01 itself caches NO decisions -- every ``authorize`` call reads current
    grants, which is the strongest form of "decisions invalidate promptly on grant
    change". This counter exists for CONSUMERS that do cache, and for the
    ``policy_version`` field of RoleGrantsChanged.v1, so a consumer can tell that
    its cached answer predates a change.
    """

    school_id = models.UUIDField(primary_key=True)
    version = models.IntegerField(default=1)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "access_policy_version"

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"PolicyVersion {self.school_id} v{self.version}"
