"""Closed request serializers for M12 files."""

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
            forbidden = {"school_id", "actor_id", "resource_grant"}
            carried = sorted(set(data) & forbidden)
            if carried:
                raise serializers.ValidationError(
                    dict.fromkeys(carried, "error.server_internal_field_rejected")
                )
        return super().to_internal_value(data)


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape for spectacular."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.DictField(required=False)


class BeginUploadRequest(ClosedSerializer):
    """POST /uploads body."""

    purpose = serializers.ChoiceField(
        choices=[
            "answer_sheet",
            "import_csv",
            "import_xlsx",
            "report_pdf",
            "report_csv",
            "report_xlsx",
        ]
    )
    client_name = serializers.CharField(min_length=1, max_length=255)
    declared_bytes = serializers.IntegerField(min_value=1)
    mime = serializers.CharField(min_length=1)


class CompleteUploadRequest(ClosedSerializer):
    """POST /uploads/{id}/complete body."""

    source_sha256 = serializers.RegexField(
        regex=r"^[a-f0-9]{64}$", min_length=64, max_length=64
    )


class QualityConfirmationRequest(ClosedSerializer):
    """POST /files/{id}/quality-confirmation body."""

    candidate_version = serializers.IntegerField(min_value=1)
    readability_confirmed = serializers.BooleanField()

    def validate_readability_confirmed(self, value: bool) -> bool:
        """Only true is accepted."""
        if value is not True:
            raise serializers.ValidationError("error.validation_failed")
        return value


class ReprocessRequest(ClosedSerializer):
    """POST /files/{id}/reprocess body."""

    profile = serializers.ChoiceField(choices=["higher_fidelity"])
    reason = serializers.CharField(min_length=1, max_length=500)


class RetentionHoldRequest(ClosedSerializer):
    """POST /files/{id}/retention-hold body."""

    legal_hold = serializers.BooleanField()
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=1, max_length=500, required=False)
