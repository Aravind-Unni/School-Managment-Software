"""DRF serializers for M06. Closed request bodies."""

from __future__ import annotations

from rest_framework import serializers


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape for OpenAPI."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.ListField(child=serializers.DictField(), required=False)


class CreateWarningRuleRequest(serializers.Serializer):
    """POST /warning-rules body."""

    code = serializers.CharField(min_length=1, max_length=64)
    threshold = serializers.CharField(min_length=1, max_length=32)
    window = serializers.CharField(min_length=1, max_length=32)
    minimum_samples = serializers.IntegerField(min_value=1)
    exclusions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class WarningActionRequest(serializers.Serializer):
    """Acknowledge/dismiss body."""

    reason = serializers.CharField(min_length=1)
    expected_version = serializers.IntegerField(min_value=1)


class CreateInterventionRequest(serializers.Serializer):
    """POST /interventions body."""

    student_id = serializers.UUIDField()
    goal = serializers.CharField(min_length=1)
    owner_id = serializers.UUIDField()
    review_date = serializers.DateField()
    resource_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    visibility = serializers.ChoiceField(choices=["staff", "guardian_visible", "restricted"])


class CreateMeetingRequest(serializers.Serializer):
    """POST /meetings body."""

    student_id = serializers.UUIDField()
    date = serializers.DateField()
    participants = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    notes = serializers.CharField(allow_blank=True)
    actions = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    visibility = serializers.ChoiceField(choices=["staff", "guardian_visible", "restricted"])
