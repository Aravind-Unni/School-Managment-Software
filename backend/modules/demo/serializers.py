"""Request serializers for the demo API.

Response shaping lives in the service's ``to_wire``, not here, so the wire
contract is defined in one place and the OpenAPI schema is generated from it.
"""

from __future__ import annotations

from rest_framework import serializers


class CreateNoteRequest(serializers.Serializer):
    """Body for POST /api/demo/notes/."""

    body = serializers.CharField(max_length=4000, allow_blank=False)
    # Mandatory: the read rule is relationship-gated, so a subjectless note
    # could never be read back by anyone.
    subject_person_id = serializers.UUIDField(required=True)


class UpdateNoteRequest(serializers.Serializer):
    """Body for PATCH /api/demo/notes/<id>/.

    ``expected_version`` is mandatory: an update without it would be a
    last-write-wins overwrite, which the platform forbids.
    """

    body = serializers.CharField(max_length=4000, allow_blank=False)
    expected_version = serializers.IntegerField(min_value=1)


class FieldErrorResponse(serializers.Serializer):
    """One field-scoped problem inside the shared error envelope."""

    field = serializers.CharField()
    message_key = serializers.CharField()


class ErrorEnvelopeResponse(serializers.Serializer):
    """The frozen error body returned by every non-2xx response.

    Declared here only so that drf-spectacular emits it as a reusable component;
    the authoritative definition is contracts/common/error-envelope.schema.json.
    """

    code = serializers.ChoiceField(
        choices=[
            "unauthenticated",
            "stale_auth",
            "action_denied",
            "object_inaccessible",
            "version_conflict",
            "state_conflict",
            "validation_failed",
        ]
    )
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = FieldErrorResponse(many=True)


class NoteResponse(serializers.Serializer):
    """One demo note as returned by the API."""

    id = serializers.UUIDField()
    school_id = serializers.UUIDField()
    body = serializers.CharField()
    version = serializers.IntegerField(min_value=1)
    section_id = serializers.UUIDField(allow_null=True)
    subject_person_id = serializers.UUIDField(allow_null=True)


class NoteCollectionResponse(serializers.Serializer):
    """The paginated collection envelope: items plus an opaque next_cursor."""

    items = NoteResponse(many=True)
    next_cursor = serializers.CharField(allow_null=True)
