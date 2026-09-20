"""Closed request serializers for M10 alumni."""

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


class ContactFieldsSerializer(ClosedSerializer):
    """Optional contact field bundle."""

    email = serializers.CharField(required=False, allow_null=True, allow_blank=False)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=False)
    postal_address = serializers.CharField(required=False, allow_null=True, allow_blank=False)


class PreferenceSpecSerializer(ClosedSerializer):
    """One preference upsert in approve/patch bodies."""

    purpose = serializers.ChoiceField(choices=["alumni_notice", "directory"])
    channel = serializers.ChoiceField(choices=["email", "sms", "postal", "phone"])
    allowed = serializers.BooleanField()


class ContactPolicySerializer(ClosedSerializer):
    """Optional contact seed on approve."""

    fields = ContactFieldsSerializer(required=False)
    preferences = PreferenceSpecSerializer(many=True, required=False)


class ApproveCandidateRequest(ClosedSerializer):
    """POST /alumni/candidates/{id}/approve body."""

    include = serializers.BooleanField()
    reason = serializers.CharField(min_length=1)
    contact_policy = ContactPolicySerializer(required=False)


class PatchContactRequest(ClosedSerializer):
    """PATCH /alumni/{id}/contact body."""

    fields = ContactFieldsSerializer(required=False)
    preferences = PreferenceSpecSerializer(many=True, required=False)
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=1)


class ExportFiltersSerializer(ClosedSerializer):
    """Export filter bag."""

    year = serializers.IntegerField(required=False, allow_null=True, min_value=1900)
    outcome = serializers.ChoiceField(
        choices=["graduate", "transfer"], required=False, allow_null=True
    )


class CreateExportRequest(ClosedSerializer):
    """POST /alumni/exports body."""

    filters = ExportFiltersSerializer()
    fields = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                "display_name",
                "admission_no",
                "leaving_year",
                "outcome",
                "email",
                "phone",
                "postal_address",
            ]
        ),
        allow_empty=False,
    )
