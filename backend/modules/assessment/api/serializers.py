"""DRF serializers for M05 assessment. Closed request bodies."""

from __future__ import annotations

from rest_framework import serializers


class ErrorEnvelopeResponse(serializers.Serializer):
    """Frozen error envelope shape for OpenAPI."""

    code = serializers.CharField()
    message_key = serializers.CharField()
    request_id = serializers.CharField()
    field_errors = serializers.ListField(child=serializers.DictField(), required=False)


class ComponentInput(serializers.Serializer):
    """One component on create."""

    id = serializers.UUIDField(required=False)
    max_score = serializers.RegexField(regex=r"^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$")
    weight = serializers.RegexField(regex=r"^(0|1|0\.[0-9]{1,3}|1\.0{1,3})$")
    topic = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=200
    )
    question_type = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=80
    )


class CreateAssessmentRequest(serializers.Serializer):
    """POST /assessments body."""

    year_id = serializers.UUIDField()
    term_id = serializers.UUIDField()
    section_id = serializers.UUIDField()
    subject_id = serializers.UUIDField()
    type = serializers.ChoiceField(
        choices=["assignment", "written_test", "practical", "project", "exam"]
    )
    title = serializers.CharField(required=False, allow_blank=True, max_length=120)
    components = ComponentInput(many=True, allow_empty=False)
    policy_version = serializers.CharField(min_length=1, max_length=64)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    max_score = serializers.CharField(required=False, allow_null=True)


class ComponentScoreInput(serializers.Serializer):
    """One component score in a PATCH body."""

    component_id = serializers.UUIDField()
    score = serializers.RegexField(regex=r"^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$")


class PatchResultRequest(serializers.Serializer):
    """PATCH /assessments/{id}/results/{student_id} body."""

    expected_version = serializers.IntegerField(min_value=1)
    attempt_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=["draft", "submitted", "approved", "published", "reopened"]
    )
    marking_outcome = serializers.ChoiceField(
        choices=["scored", "absent", "exempt", "oral", "practical"],
        required=False,
    )
    component_scores = ComponentScoreInput(many=True, required=False)


class EvidencePageInput(serializers.Serializer):
    """One evidence page to bind."""

    file_id = serializers.UUIDField()
    canonical_version = serializers.IntegerField(min_value=1)
    page_no = serializers.IntegerField(min_value=1)


class BindEvidenceRequest(serializers.Serializer):
    """POST /results/{id}/evidence body."""

    expected_version = serializers.IntegerField(min_value=1)
    pages = EvidencePageInput(many=True, allow_empty=False)


class ExpectedVersionBody(serializers.Serializer):
    """Submit / approve / reopen body."""

    expected_version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=500
    )


class PublicationRequest(serializers.Serializer):
    """POST /assessments/{id}/publication body."""

    expected_version = serializers.IntegerField(min_value=1)
