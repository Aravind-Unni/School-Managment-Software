"""DRF serializers for M04 attendance. Closed request bodies."""

from __future__ import annotations

from rest_framework import serializers


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape for OpenAPI."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.ListField(child=serializers.DictField(), required=False)


class CreateSessionRequest(serializers.Serializer):
    """POST /attendance/sessions body."""

    timetable_session_id = serializers.UUIDField()


class SaveEntryInput(serializers.Serializer):
    """One writable mark in a save body."""

    enrolment_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=["present", "absent", "late", "excused"])
    note = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=500
    )


class SaveSessionRequest(serializers.Serializer):
    """PUT /attendance/sessions/{id} body."""

    expected_version = serializers.IntegerField(min_value=1)
    entries = SaveEntryInput(many=True)


class SubmitSessionRequest(serializers.Serializer):
    """POST /attendance/sessions/{id}/submit body."""

    expected_version = serializers.IntegerField(min_value=1)


class CorrectionRequest(serializers.Serializer):
    """POST /attendance/entries/{id}/corrections body."""

    status = serializers.ChoiceField(choices=["present", "absent", "late", "excused"])
    reason = serializers.CharField(min_length=1, max_length=500)
    expected_version = serializers.IntegerField(min_value=1)
