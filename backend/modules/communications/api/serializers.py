"""Closed request serializers for M11 communications."""

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


class AudienceSelectorSerializer(ClosedSerializer):
    """Closed audience selector: section or person_ids."""

    kind = serializers.ChoiceField(choices=["section", "person_ids"])
    section_id = serializers.UUIDField(required=False)
    person_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=False
    )


class CreateNoticeRequest(ClosedSerializer):
    """POST /notices body."""

    title = serializers.CharField(min_length=1, max_length=200)
    body = serializers.CharField(min_length=1, max_length=20000)
    locale = serializers.ChoiceField(choices=["en", "ml"])
    audience = AudienceSelectorSerializer()
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class PublishNoticeRequest(ClosedSerializer):
    """POST /notices/{id}/publish body."""

    expected_version = serializers.IntegerField(min_value=1)


class EnqueueMessageRequest(ClosedSerializer):
    """POST /messages body."""

    template_key = serializers.CharField(min_length=1, max_length=100)
    recipient_ref = serializers.UUIDField()
    locale = serializers.ChoiceField(choices=["en", "ml"])
    variables = serializers.DictField(child=serializers.JSONField(), allow_empty=True)
    channel = serializers.ChoiceField(choices=["in_app", "sms"])
    dedupe_key = serializers.CharField(min_length=1, max_length=200)
