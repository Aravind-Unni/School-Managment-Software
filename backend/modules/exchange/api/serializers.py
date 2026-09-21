"""Closed request serializers for M13 exchange.

Closed on purpose: the frozen schemas set ``additionalProperties: false``, and
an open serializer would accept a ``school_id`` or a ``resource_grant`` the
client had no business sending.
"""

from __future__ import annotations

from rest_framework import serializers

from ..adapters import export_datasets, import_datasets

#: Fields the server derives and must never accept from a browser. Named so the
#: refusal says which one was sent rather than a generic "unknown field".
SERVER_INTERNAL_FIELDS = frozenset(
    {"school_id", "actor_id", "resource_grant", "auth_level", "relationship"}
)


class ClosedSerializer(serializers.Serializer):
    """Refuse fields the serializer does not declare.

    A server-internal field gets its own message key, because "you sent
    something the server decides" is a different mistake from a typo and a
    developer should be told which one they made.
    """

    def to_internal_value(self, data):
        """Reject server-internal keys, then unknown keys, then parse normally."""
        if isinstance(data, dict):
            internal = sorted(set(data) & SERVER_INTERNAL_FIELDS)
            if internal:
                raise serializers.ValidationError(
                    dict.fromkeys(internal, "error.server_internal_field_rejected")
                )
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    dict.fromkeys(unknown, "error.field_not_accepted")
                )
        return super().to_internal_value(data)


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape, for the generated schema."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.DictField(required=False)


class CreateImportRequest(ClosedSerializer):
    """POST /imports body."""

    dataset = serializers.ChoiceField(choices=list(import_datasets()))
    file_ref = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=["validate"])


class CommitImportRequest(ClosedSerializer):
    """POST /imports/{id}/commit body."""

    validation_version = serializers.IntegerField(min_value=1)
    source_digest = serializers.RegexField(r"^[a-f0-9]{64}$", min_length=64, max_length=64)


class CreateExportRequest(ClosedSerializer):
    """POST /exports body."""

    dataset = serializers.ChoiceField(choices=list(export_datasets()))
    filters = serializers.DictField(child=serializers.JSONField(), allow_empty=True)
    fields = serializers.ListField(child=serializers.CharField(min_length=1), allow_empty=False)
    format = serializers.ChoiceField(choices=["csv", "xlsx", "pdf"])
    locale = serializers.ChoiceField(choices=["en", "ml"])


class CreateReportCardsRequest(ClosedSerializer):
    """POST /reportcards body."""

    publication_id = serializers.UUIDField()
    student_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    locale = serializers.ChoiceField(choices=["en", "ml"])
    template_version = serializers.CharField(min_length=1, max_length=64)
