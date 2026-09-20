"""M05 REST endpoints for assessments and results."""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import deps
from .serializers import (
    BindEvidenceRequest,
    CreateAssessmentRequest,
    ErrorEnvelopeResponse,
    ExpectedVersionBody,
    PatchResultRequest,
    PublicationRequest,
)

COMMON_ERRORS = {
    400: OpenApiResponse(ErrorEnvelopeResponse, "Client asserted its own identity."),
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated, or 2FA too old."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}


def validated(serializer_class, data) -> dict:
    """Parse a closed request body, raising 422 on anything unexpected."""
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


class AssessmentCollectionView(APIView):
    """POST /assessments."""

    @extend_schema(
        operation_id="create_assessment",
        request=CreateAssessmentRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a draft assessment structure."""
        body = validated(CreateAssessmentRequest, request.data)
        created = deps.create_service().create(
            request.school_context,
            year_id=body["year_id"],
            term_id=body["term_id"],
            section_id=body["section_id"],
            subject_id=body["subject_id"],
            assessment_type=body["type"],
            components=body["components"],
            policy_version=body["policy_version"],
            due_at=body.get("due_at"),
            max_score=body.get("max_score"),
        )
        return Response(created, status=status.HTTP_201_CREATED)


class ResultPatchView(APIView):
    """PATCH /assessments/{id}/results/{student_id}."""

    @extend_schema(
        operation_id="patch_result_marks",
        request=PatchResultRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def patch(self, request: Request, assessment_id: UUID, student_id: UUID) -> Response:
        """Edit marks for one student result."""
        body = validated(PatchResultRequest, request.data)
        return Response(
            deps.marks_service().patch(
                request.school_context,
                assessment_id=assessment_id,
                student_id=student_id,
                expected_version=body["expected_version"],
                attempt_id=body["attempt_id"],
                status=body["status"],
                marking_outcome=body.get("marking_outcome"),
                component_scores=body.get("component_scores"),
            )
        )


class ResultEvidenceView(APIView):
    """POST /results/{id}/evidence."""

    @extend_schema(
        operation_id="bind_result_evidence",
        request=BindEvidenceRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, result_id: UUID) -> Response:
        """Bind ordered quality-confirmed answer-sheet pages."""
        body = validated(BindEvidenceRequest, request.data)
        return Response(
            deps.evidence_service().bind(
                request.school_context,
                result_id=result_id,
                expected_version=body["expected_version"],
                pages=body["pages"],
            )
        )


class AssessmentSubmitView(APIView):
    """POST /assessments/{id}/submit."""

    @extend_schema(
        operation_id="submit_assessment",
        request=ExpectedVersionBody,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, assessment_id: UUID) -> Response:
        """Submit a draft for review."""
        body = validated(ExpectedVersionBody, request.data)
        return Response(
            deps.workflow_service().submit(
                request.school_context,
                assessment_id=assessment_id,
                expected_version=body["expected_version"],
            )
        )


class AssessmentApproveView(APIView):
    """POST /assessments/{id}/approve."""

    @extend_schema(
        operation_id="approve_assessment",
        request=ExpectedVersionBody,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, assessment_id: UUID) -> Response:
        """Approve a submitted assessment."""
        body = validated(ExpectedVersionBody, request.data)
        return Response(
            deps.workflow_service().approve(
                request.school_context,
                assessment_id=assessment_id,
                expected_version=body["expected_version"],
            )
        )


class AssessmentPublicationView(APIView):
    """POST /assessments/{id}/publication."""

    @extend_schema(
        operation_id="publish_assessment",
        request=PublicationRequest,
        responses={200: dict, **COMMON_ERRORS},
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                str,
                OpenApiParameter.HEADER,
                required=True,
            )
        ],
    )
    def post(self, request: Request, assessment_id: UUID) -> Response:
        """Publish approved results. Requires Idempotency-Key and recent 2FA."""
        body = validated(PublicationRequest, request.data)
        key = request.headers.get("Idempotency-Key") or request.META.get(
            "HTTP_IDEMPOTENCY_KEY", ""
        )
        return Response(
            deps.publish_service().publish(
                request.school_context,
                assessment_id=assessment_id,
                expected_version=body["expected_version"],
                idempotency_key=key,
            )
        )


class AssessmentReopenView(APIView):
    """POST /assessments/{id}/reopen."""

    @extend_schema(
        operation_id="reopen_assessment",
        request=ExpectedVersionBody,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, assessment_id: UUID) -> Response:
        """Reopen a published assessment for correction."""
        body = validated(ExpectedVersionBody, request.data)
        return Response(
            deps.reopen_service().reopen(
                request.school_context,
                assessment_id=assessment_id,
                expected_version=body["expected_version"],
                reason=body.get("reason"),
            )
        )


class EvidenceViewView(APIView):
    """GET /results/{id}/evidence/{binding_id}/view."""

    @extend_schema(
        operation_id="view_result_evidence",
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request, result_id: UUID, binding_id: UUID) -> Response:
        """Issue a short-lived read URL for one evidence binding."""
        return Response(
            deps.evidence_service().view(
                request.school_context,
                result_id=result_id,
                binding_id=binding_id,
            )
        )
