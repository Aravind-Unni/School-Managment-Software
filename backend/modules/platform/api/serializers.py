"""Closed request serializers for M14."""

from __future__ import annotations

from rest_framework import serializers


class ErrorEnvelopeResponse(serializers.Serializer):
    """Stable error envelope for spectacular docs."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
    request_id = serializers.CharField()


class RetryJobRequest(serializers.Serializer):
    """POST /jobs/{id}/retry body."""

    reason = serializers.CharField(min_length=1, max_length=500)


class CreateRestoreRehearsalRequest(serializers.Serializer):
    """POST /operations/restore-rehearsals body."""

    backup_manifest_id = serializers.UUIDField()
    isolated_target_label = serializers.CharField(min_length=1, max_length=128)
