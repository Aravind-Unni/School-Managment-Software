"""Closed request serializers for M09 library."""

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


class CreateTitleRequest(ClosedSerializer):
    """POST /library/titles body."""

    name = serializers.CharField(min_length=1)
    author = serializers.CharField(min_length=1)
    language = serializers.CharField(min_length=1)
    isbn = serializers.CharField(required=False, allow_null=True, allow_blank=False)


class CreateCopyRequest(ClosedSerializer):
    """POST /library/copies body."""

    title_id = serializers.UUIDField()
    accession_no = serializers.CharField(min_length=1)


class CreateLoanRequest(ClosedSerializer):
    """POST /library/loans body."""

    copy_id = serializers.UUIDField()
    borrower_person_id = serializers.UUIDField()
    borrower_type = serializers.ChoiceField(choices=["student", "staff"])
    due_date = serializers.DateField()


class ReturnLoanRequest(ClosedSerializer):
    """POST /library/loans/{id}/return body."""

    returned_at = serializers.DateTimeField()
    condition = serializers.ChoiceField(choices=["ok", "damaged", "lost"])
    expected_version = serializers.IntegerField(min_value=1)


class RenewLoanRequest(ClosedSerializer):
    """POST /library/loans/{id}/renew body."""

    new_due_date = serializers.DateField()
    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_null=True, allow_blank=False)


class AdjustCopyRequest(ClosedSerializer):
    """POST /library/copies/{id}/adjust body."""

    new_state = serializers.ChoiceField(
        choices=["available", "on_loan", "lost", "damaged", "withdrawn"]
    )
    reason = serializers.CharField(min_length=1)
    expected_version = serializers.IntegerField(min_value=1)


class CatalogueImportRowSerializer(ClosedSerializer):
    """One import row."""

    name = serializers.CharField(min_length=1)
    author = serializers.CharField(min_length=1)
    language = serializers.CharField(min_length=1)
    accession_no = serializers.CharField(min_length=1)
    isbn = serializers.CharField(required=False, allow_null=True, allow_blank=False)


class CatalogueImportRequest(ClosedSerializer):
    """POST /library/catalogue-imports body."""

    rows = CatalogueImportRowSerializer(many=True, allow_empty=False)
