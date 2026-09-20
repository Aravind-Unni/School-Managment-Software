"""Closed request serializers for M07 fees."""

from __future__ import annotations

from rest_framework import serializers


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape for spectacular."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.DictField(required=False)


class CreateFeePlanRequest(serializers.Serializer):
    """POST /fee-plans body."""

    fee_heads = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    applicability = serializers.DictField(required=False, default=dict)
    schedule = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    version = serializers.IntegerField(min_value=1)


class CreateChargeRequest(serializers.Serializer):
    """POST /charges body."""

    student_id = serializers.UUIDField()
    fee_head_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField()
    due_date = serializers.DateField()
    source_key = serializers.CharField(max_length=256)
    description_key = serializers.CharField(required=False, allow_blank=True, default="")


class AllocationInput(serializers.Serializer):
    """One payment allocation line."""

    charge_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField()


class CreatePaymentRequest(serializers.Serializer):
    """POST /payments body."""

    student_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField()
    method = serializers.ChoiceField(choices=["cash", "bank", "upi"])
    reference = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    allocations = AllocationInput(many=True, allow_empty=False)


class CreateReversalRequest(serializers.Serializer):
    """POST /payments/{id}/reversals body."""

    reason = serializers.CharField(allow_blank=False)
    expected_version = serializers.IntegerField(min_value=1)


class CreateConcessionRequest(serializers.Serializer):
    """POST /concessions body."""

    charge_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField()
    reason = serializers.CharField(allow_blank=False)
    source_key = serializers.CharField(max_length=256)
    major = serializers.BooleanField(required=False, default=False)


class CreateRefundRequest(serializers.Serializer):
    """POST /refunds body."""

    student_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField()
    reason = serializers.CharField(allow_blank=False)
    credit_id = serializers.UUIDField(required=False, allow_null=True)
