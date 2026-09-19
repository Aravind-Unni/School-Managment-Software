"""Factor enrolment, replacement and administrator-approved reset.

Rules this file enforces:
  * A fresh password confirmation is required to enrol, replace or disable a factor.
  * The secret and the recovery codes are returned exactly ONCE. Only ciphertext and
    hashes are stored, so nobody -- including an administrator -- can re-display them.
  * A protected role's required factor cannot be disabled.
  * A reset is approved by a DIFFERENT authorised person, revokes the old factor and
    every session, and notifies the account. A password reset alone never disables 2FA.
  * There is no SMS fallback anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db import IntegrityError, transaction

from contracts.errors import ActionDenied, ObjectInaccessible, StateConflict

from ..models.accounts import CaseState, FactorState
from . import sessions
from .crypto import (
    encrypt_secret,
    generate_recovery_codes,
    hash_recovery_code,
    new_totp_secret,
)
from .login import require_recent_password_confirmation, two_factor_required_for
from .totp import (
    TOTP_DIGITS,
    TOTP_PERIOD_SECONDS,
    TotpVerificationError,
    accept_code,
    provisioning_uri,
)

#: Shown in the authenticator app. A school deployment may override it.
DEFAULT_ISSUER = "School Platform"


@dataclass(frozen=True, slots=True)
class Enrolment:
    """One-time provisioning data. Never persisted in this form, never logged."""

    factor_id: UUID
    secret_base32: str
    otpauth_uri: str
    issuer: str
    account_name: str

    def to_wire(self) -> dict[str, object]:
        """Serialise for the single response that may carry the secret."""
        return {
            "factor_id": str(self.factor_id),
            "secret_base32": self.secret_base32,
            "otpauth_uri": self.otpauth_uri,
            "digits": TOTP_DIGITS,
            "period_seconds": TOTP_PERIOD_SECONDS,
            "issuer": self.issuer,
            "account_name": self.account_name,
        }


def start_enrolment(*, user, instant: datetime, issuer: str = DEFAULT_ISSUER) -> Enrolment:
    """Create a PENDING factor and return its provisioning data.

    Requires a recent password confirmation. Refuses when an active factor already
    exists -- replacing one goes through the same path but must revoke the old factor
    first, which is an explicit act rather than a side effect.

    Any previous PENDING factor is discarded, so an abandoned enrolment cannot be
    confirmed later by someone who captured its QR code.
    """
    from ..models import TotpFactor

    require_recent_password_confirmation(user=user, instant=instant)

    if TotpFactor.objects.filter(user=user, state=FactorState.ACTIVE).exists():
        raise StateConflict("error.factor_already_active")

    TotpFactor.objects.filter(user=user, state=FactorState.PENDING).delete()

    secret = new_totp_secret()
    factor = TotpFactor.objects.create(
        school_id=user.school_id,
        user=user,
        encrypted_secret=encrypt_secret(secret),
        state=FactorState.PENDING,
        created_at=instant,
    )
    return Enrolment(
        factor_id=factor.id,
        secret_base32=secret,
        otpauth_uri=provisioning_uri(secret, account_name=user.login_name, issuer=issuer),
        issuer=issuer,
        account_name=user.login_name,
    )


def confirm_enrolment(
    *, user, factor_id: UUID, code: str, instant: datetime
) -> tuple[object, tuple[str, ...]]:
    """Activate a pending factor and return it with fresh recovery codes.

    The codes are returned ONCE and stored only as hashes. Proving the code works
    before activating is what stops an account locking itself out with a
    mistyped secret.
    """
    from ..models import RecoveryCode, TotpFactor

    require_recent_password_confirmation(user=user, instant=instant)

    with transaction.atomic():
        factor = (
            TotpFactor.objects.select_for_update()
            .filter(id=factor_id, user=user, state=FactorState.PENDING)
            .first()
        )
        if factor is None:
            raise ObjectInaccessible("error.object_inaccessible")
        if TotpFactor.objects.filter(user=user, state=FactorState.ACTIVE).exists():
            raise StateConflict("error.factor_already_active")

        try:
            accept_code(factor, code, instant=instant)
        except TotpVerificationError as exc:
            from contracts.errors import ValidationFailed

            raise ValidationFailed("error.totp_code_invalid") from exc

        factor.state = FactorState.ACTIVE
        factor.activated_at = instant
        factor.version += 1
        factor.save(update_fields=["state", "activated_at", "version", "last_accepted_step"])

        codes = generate_recovery_codes()
        # Invalidate the previous UNUSED codes: a code issued against a revoked
        # factor must not still work. Already-used codes are KEPT, for two reasons:
        # they are spent so they cannot be reused, and deleting them would erase the
        # record of which code was consumed -- and would turn a replay attempt into
        # a confusing "invalid code" instead of the correct "already used".
        RecoveryCode.objects.filter(user=user, used_at__isnull=True).delete()
        RecoveryCode.objects.bulk_create(
            [
                RecoveryCode(
                    school_id=user.school_id,
                    user=user,
                    code_hash=hash_recovery_code(code_value, school_id=user.school_id),
                    created_at=instant,
                )
                for code_value in codes
            ]
        )
        return factor, codes


def disable_factor(*, user, instant: datetime) -> None:
    """Revoke the active factor, unless policy protects it.

    Refuses for an account whose role requires a factor: a protected staff account
    cannot drop to password-only. Requires a recent password confirmation.
    """
    from ..models import TotpFactor

    require_recent_password_confirmation(user=user, instant=instant)
    if two_factor_required_for(user):
        raise ActionDenied("error.required_factor_protected")

    TotpFactor.objects.filter(user=user, state=FactorState.ACTIVE).update(
        state=FactorState.REVOKED, revoked_at=instant
    )


def open_reset_case(*, user, reason: str, instant: datetime):
    """Open a lost-device identity-verification case.

    Refuses a second concurrent case, so a flood of requests cannot confuse an
    approver into approving the wrong one. The unique constraint is the real
    guard; this converts the database error into a clean 409.
    """
    from ..models import RecoveryCase

    try:
        with transaction.atomic():
            return RecoveryCase.objects.create(
                school_id=user.school_id,
                user=user,
                reason=reason[:1000],
                state=CaseState.PENDING,
                created_at=instant,
            )
    except IntegrityError as exc:
        raise StateConflict("error.case_not_pending") from exc


def approve_reset_case(*, case_id: UUID, approver, instant: datetime):
    """Approve a case, reset the factor and revoke everything it authorised.

    The approver may NEVER be the subject -- that is the whole point of a
    second-person check, and it is enforced here rather than left to the caller.

    Owner recovery uses the company-controlled verified process and does not require
    a second owner to exist, so no such requirement appears here.

    Returns the case and how many sessions were revoked, so the caller can audit
    the blast radius.
    """
    from ..models import RecoveryCase, RecoveryCode, TotpFactor

    with transaction.atomic():
        case = (
            RecoveryCase.objects.select_for_update()
            .select_related("user")
            .filter(id=case_id, school_id=approver.school_id)
            .first()
        )
        if case is None:
            raise ObjectInaccessible("error.object_inaccessible")
        if case.state != CaseState.PENDING:
            raise StateConflict("error.case_not_pending")
        if case.user_id == approver.id:
            raise ActionDenied("error.action_denied")

        subject = case.user
        TotpFactor.objects.filter(user=subject).exclude(state=FactorState.REVOKED).update(
            state=FactorState.REVOKED, revoked_at=instant
        )
        # Old recovery codes die with the factor, or a code from the lost
        # authenticator's set would still grant access.
        RecoveryCode.objects.filter(user=subject, used_at__isnull=True).delete()
        revoked = sessions.revoke_all_for_user(subject, instant=instant)

        case.state = CaseState.APPROVED
        case.approver = approver
        case.decided_at = instant
        case.version += 1
        case.save(update_fields=["state", "approver", "decided_at", "version"])
        return case, revoked


def describe_case(case) -> dict[str, object]:
    """Serialise a recovery case for the API."""
    return {
        "id": str(case.id),
        "user_id": str(case.user_id),
        "state": case.state,
        "reason": case.reason,
        "approver_id": str(case.approver_id) if case.approver_id else None,
        "created_at": case.created_at.isoformat(),
        "decided_at": case.decided_at.isoformat() if case.decided_at else None,
        "version": case.version,
    }
