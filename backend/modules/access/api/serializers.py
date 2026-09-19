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
