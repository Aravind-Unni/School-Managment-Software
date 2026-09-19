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
