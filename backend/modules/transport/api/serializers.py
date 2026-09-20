"""Closed request serializers for M08 transport."""

from __future__ import annotations

from rest_framework import serializers


class ClosedSerializer(serializers.Serializer):
    """Refuse fields the serializer does not declare."""

    def to_internal_value(self, data):
        """Reject unknown keys, then parse normally."""
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    dict.fromkeys(unknown, "error.field_not_accepted")
                )
        return super().to_internal_value(data)


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape for spectacular."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.DictField(required=False)


class CreateBusRequest(ClosedSerializer):
    """POST /buses body."""

    label = serializers.CharField(min_length=1)
    active = serializers.BooleanField(required=False, default=True)


class CreateParticipationRequest(ClosedSerializer):
    """POST /bus-participations body."""

    student_id = serializers.UUIDField()
    from_date = serializers.DateField()
    fee_plan_id = serializers.UUIDField()
    bus_id = serializers.UUIDField(required=False, allow_null=True)


class PatchParticipationRequest(ClosedSerializer):
    """PATCH /bus-participations/{id} body."""

    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=1)
    to_date = serializers.DateField(required=False, allow_null=True)
    bus_id = serializers.UUIDField(required=False, allow_null=True)


class CreateBillingRunRequest(ClosedSerializer):
    """POST /bus-billing-runs body."""

    period = serializers.RegexField(regex=r"^[0-9]{4}-[0-9]{2}$")
    policy_version = serializers.IntegerField(min_value=1)


class CreateAdjustmentRequest(ClosedSerializer):
    """POST /bus-adjustments body."""

    charge_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=1)
    source_key = serializers.CharField(min_length=1)
