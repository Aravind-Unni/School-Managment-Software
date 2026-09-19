"""Request serializers for M01.

Every write serializer sets ``unknown_field_policy`` via ``StrictSerializer``, so an
undeclared field is a 422 naming the offender rather than a silently ignored value.
Response shaping lives in the services' ``describe_*`` helpers, so the wire contract
is defined once.
"""

from __future__ import annotations

from rest_framework import serializers

from contracts.errors import FieldError, ValidationFailed


class StrictSerializer(serializers.Serializer):
    """A serializer that refuses unknown fields.

    DRF ignores undeclared keys by default. For an identity API that is dangerous:
    a client sending ``{"expected_version": 1}`` to an endpoint that spells it
    differently would silently get a last-write-wins overwrite.
    """

    def to_internal_value(self, data):
        """Reject undeclared keys before normal validation."""
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise ValidationFailed(
                    "error.unknown_field",
                    field_errors=tuple(
                        FieldError(name, "error.unknown_field") for name in unknown
                    ),
                )
        return super().to_internal_value(data)


class LoginRequest(StrictSerializer):
    """Body for POST /auth/login."""

    login_name = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=1024, trim_whitespace=False)


class TotpVerifyRequest(StrictSerializer):
    """Body for POST /auth/2fa/verify."""

    challenge_id = serializers.UUIDField()
    code = serializers.RegexField(r"^[0-9]{6}$")


class PasswordConfirmRequest(StrictSerializer):
    """Body for endpoints needing a fresh password confirmation.

    ``challenge_id`` is supplied for a FIRST enrolment, where the account has no
    session yet: a role that requires a factor cannot sign in without one, so
    enrolment must be reachable from the challenge. Omitted when replacing a factor
    from an existing session.
    """

    password = serializers.CharField(max_length=1024, trim_whitespace=False)
    challenge_id = serializers.UUIDField(required=False, allow_null=True)


class EnrolConfirmRequest(StrictSerializer):
    """Body for POST /auth/2fa/confirm.

    On the first-enrolment path ``challenge_id`` is present and confirming the
    factor also completes the login, so the account is not asked to authenticate
    twice in a row for no reason.
    """

    factor_id = serializers.UUIDField()
    code = serializers.RegexField(r"^[0-9]{6}$")
    password = serializers.CharField(max_length=1024, trim_whitespace=False)
    challenge_id = serializers.UUIDField(required=False, allow_null=True)


class RecoverRequest(StrictSerializer):
    """Body for POST /auth/2fa/recover."""

    challenge_id = serializers.UUIDField()
    recovery_code = serializers.CharField(max_length=32)


class ResetRequestBody(StrictSerializer):
    """Body for POST /auth/factor/reset-requests."""

    reason = serializers.CharField(max_length=1000)


class GrantBody(StrictSerializer):
    """One grant inside a role write."""

    action = serializers.CharField(max_length=128)
    scope_type = serializers.ChoiceField(choices=["school", "section", "subject", "self"])
    scope_id = serializers.UUIDField(required=False, allow_null=True)
    valid_from = serializers.DateField()
    valid_to = serializers.DateField(required=False, allow_null=True)


class RoleWriteRequest(StrictSerializer):
    """Body for POST /roles and PUT /roles/{id}/grants."""

    name = serializers.CharField(max_length=100)
    requires_two_factor = serializers.BooleanField(required=False, default=False)
    grants = GrantBody(many=True)
    expected_version = serializers.IntegerField(required=False, min_value=1)


# ---------------------------------------------------------------------------
# Response serializers.
#
# Declared so the generated OpenAPI carries real response bodies and the
# TypeScript client can be generated from it. The AUTHORITATIVE definitions are
# contracts/M01/schemas/dtos.schema.json; these mirror them, and a contract test
# asserts the two agree.
# ---------------------------------------------------------------------------


class FieldErrorResponse(serializers.Serializer):
    """One field-scoped problem inside the frozen error envelope."""

    field = serializers.CharField()
    message_key = serializers.CharField()


class ErrorEnvelopeResponse(serializers.Serializer):
    """The frozen error body returned by every non-2xx response."""

    code = serializers.ChoiceField(
        choices=[
            "unauthenticated",
            "stale_auth",
            "action_denied",
            "object_inaccessible",
            "version_conflict",
            "state_conflict",
            "validation_failed",
            "rate_limited",
        ]
    )
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = FieldErrorResponse(many=True)


class ChallengeResponse(serializers.Serializer):
    """A pre-authentication challenge. NOT a business session."""

    challenge_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField()
    next_action = serializers.ChoiceField(
        choices=["totp_required", "enrol_factor_required", "authenticated"]
    )


class AuthenticatedResponse(serializers.Serializer):
    """A live session's identity and level."""

    authenticated = serializers.BooleanField()
    auth_level = serializers.ChoiceField(choices=["password", "password_totp", "recovery"])
    actor_id = serializers.UUIDField(allow_null=True)
    school_id = serializers.UUIDField(allow_null=True)
    auth_time = serializers.DateTimeField()


class EnrolStartResponse(serializers.Serializer):
    """One-time provisioning data. The ONLY place the secret appears."""

    factor_id = serializers.UUIDField()
    secret_base32 = serializers.CharField()
    otpauth_uri = serializers.CharField()
    digits = serializers.IntegerField()
    period_seconds = serializers.IntegerField()
    issuer = serializers.CharField()
    account_name = serializers.CharField()


class RecoveryCodesResponse(serializers.Serializer):
    """Returned exactly once, when a factor is activated."""

    codes = serializers.ListField(child=serializers.CharField())
    generated_at = serializers.DateTimeField()
    count = serializers.IntegerField()


class SessionResponse(serializers.Serializer):
    """One of the CALLER's own sessions."""

    id = serializers.UUIDField()
    auth_level = serializers.CharField()
    auth_time = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    last_seen_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField(allow_null=True)
    is_current = serializers.BooleanField()
    user_agent_family = serializers.CharField()


class SessionCollectionResponse(serializers.Serializer):
    """Cursor page of sessions."""

    items = SessionResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class GrantResponse(serializers.Serializer):
    """One grant with its bounded scope and validity window."""

    action = serializers.CharField()
    scope_type = serializers.ChoiceField(choices=["school", "section", "subject", "self"])
    scope_id = serializers.UUIDField(allow_null=True)
    valid_from = serializers.DateField()
    valid_to = serializers.DateField(allow_null=True)


class RoleResponse(serializers.Serializer):
    """A role and its grants."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    name = serializers.CharField()
    is_owner_role = serializers.BooleanField()
    requires_two_factor = serializers.BooleanField()
    version = serializers.IntegerField()
    grants = GrantResponse(many=True)


class RoleCollectionResponse(serializers.Serializer):
    """Cursor page of roles."""

    items = RoleResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class AccountResponse(serializers.Serializer):
    """An account. Never exposes credential material or another user's factor."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    login_name = serializers.CharField()
    display_name = serializers.CharField()
    active = serializers.BooleanField()
    version = serializers.IntegerField()
    role_ids = serializers.ListField(child=serializers.UUIDField())
    has_active_factor = serializers.BooleanField()
    two_factor_required = serializers.BooleanField()


class AccountCollectionResponse(serializers.Serializer):
    """Cursor page of accounts."""

    items = AccountResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class RecoveryCaseResponse(serializers.Serializer):
    """A lost-device identity-verification case."""

    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=["pending", "approved", "rejected"])
    reason = serializers.CharField()
    approver_id = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()
    decided_at = serializers.DateTimeField(allow_null=True)
    version = serializers.IntegerField()


class RevokedResponse(serializers.Serializer):
    """Logout acknowledgement."""

    revoked = serializers.BooleanField()
