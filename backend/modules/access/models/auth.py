"""Authentication state: challenges, sessions, factors, recovery.

Nothing in this file stores a secret in the clear. TOTP seeds are encrypted with
a key held outside the database; recovery codes are stored as hashes; passwords
are hashed by Django's configured hasher.

Does not handle: accounts or permissions. That is ``models/accounts.py``.
"""

from __future__ import annotations

import uuid

from django.db import models

from .accounts import AuthLevelChoices, User


class LoginChallenge(models.Model):
    """A short-lived pre-authentication challenge.

    NOT a business session. Holding a challenge grants access to nothing: no
    business endpoint accepts it, and no session cookie exists until the required
    factor succeeds. Keeping the two separate is what stops a correct password
    alone from being usable.

    ``attempts`` is bounded; exceeding the limit invalidates the challenge rather
    than locking the account, because a permanent attacker-triggered lockout is a
    denial-of-service against the legitimate user.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="challenges")
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.IntegerField(default=0)
    #: Set when the challenge is spent. A consumed challenge can never be reused,
    #: which is what makes "only the first valid completed login works" true.
    consumed_at = models.DateTimeField(null=True, blank=True)
    #: Why the challenge was invalidated, for audit. Never shown to the client,
    #: which receives one indistinguishable message key for every failure.
    invalidated_reason = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "access_login_challenge"
        indexes = [models.Index(fields=["user", "consumed_at"])]

    def __str__(self) -> str:
        """Return a short identifier. Never includes the code or the password."""
        return f"Challenge {self.id} for {self.user_id}"


class Session(models.Model):
    """An authenticated business session.

    ``auth_time`` is when the second factor was last asserted, not when the
    session was created: a long-lived session whose factor is hours old must fail
    a step-up check, so the two are tracked separately.

    The opaque session token is stored HASHED. A leaked database row therefore
    does not yield a usable cookie.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    token_hash = models.CharField(max_length=128, unique=True)
    auth_level = models.CharField(max_length=20, choices=AuthLevelChoices.choices)
    auth_time = models.DateTimeField()
    created_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    #: Coarse client family for the "active sessions" screen. Deliberately not the
    #: raw User-Agent, which is a fingerprinting surface with no user benefit.
    user_agent_family = models.CharField(max_length=40, blank=True, default="unknown")
    #: Correlates the session with the login that created it, for audit.
    created_by_challenge_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "access_session"
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["school_id", "revoked_at"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier. Never includes the token."""
        return f"Session {self.id} ({self.auth_level})"


class TotpFactor(models.Model):
    """One RFC 6238 authenticator binding for an account.

    ``encrypted_secret`` is Fernet ciphertext; the key lives in the environment,
    never in this table, so a database dump alone does not yield working seeds.

    ``last_accepted_step`` is the heart of replay protection. A code is accepted
    only if its time step is strictly greater than the last accepted one, which
    makes acceptance atomic: the same code cannot be used twice even inside its
    own 30-second window.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="factors")
    encrypted_secret = models.BinaryField()
    state = models.CharField(max_length=16, db_index=True)
    last_accepted_step = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField()
    activated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "access_totp_factor"
        indexes = [models.Index(fields=["user", "state"])]
        constraints = [
            # At most one ACTIVE factor per account. A second active factor would
            # mean a revoked authenticator still worked.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(state="active"),
                name="access_one_active_factor_per_user",
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier. NEVER includes the secret."""
        return f"TotpFactor {self.id} ({self.state})"


class RecoveryCode(models.Model):
    """One single-use recovery code, stored as a hash.

    Ten are issued when a factor is activated and shown exactly once. Because only
    hashes are kept, neither support nor an administrator can re-display them --
    which is the point: a code an administrator can read is not a second factor.

    ``used_at`` plus a conditional unique index is what makes concurrent reuse
    resolve to exactly one winner.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    #: The session created by consuming this code, for audit.
    used_by_session_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "access_recovery_code"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "code_hash"], name="access_recovery_code_unique_per_user"
            )
        ]
        indexes = [models.Index(fields=["user", "used_at"])]

    def __str__(self) -> str:
        """Return a short identifier. NEVER includes the code value."""
        return f"RecoveryCode {self.id} used={self.used_at is not None}"


class RecoveryCase(models.Model):
    """A documented identity-verification case for a lost factor.

    Approved by a DIFFERENT authorised person; the approver may never be the
    subject. Owner recovery follows the company-controlled verified process and
    does not require a second owner to exist, so this model does not assume one.

    A password reset alone never disables 2FA -- that is why this case exists at
    all rather than the reset flow silently clearing the factor.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_cases")
    approver = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_cases"
    )
    reason = models.CharField(max_length=1000)
    state = models.CharField(max_length=16, db_index=True)
    created_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        db_table = "access_recovery_case"
        indexes = [models.Index(fields=["user", "state"])]
        constraints = [
            # At most one pending case per account, so a flood of requests cannot
            # be used to confuse an approver into approving the wrong one.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(state="pending"),
                name="access_one_pending_case_per_user",
            )
        ]

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"RecoveryCase {self.id} ({self.state})"
