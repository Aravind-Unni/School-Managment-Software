"""M10 REST endpoints for alumni candidates, directory, contact and exports."""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import deps
from .serializers import (
    ApproveCandidateRequest,
    CreateExportRequest,
    ErrorEnvelopeResponse,
    PatchContactRequest,
)

COMMON_ERRORS = {
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated."),
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


class CandidateCollectionView(APIView):
    """GET /alumni/candidates."""

    @extend_schema(
        operation_id="list_alumni_candidates",
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("state", str, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """List pending (default) or filtered candidates."""
        return Response(
            deps.candidate_service().list_candidates(
                request.school_context,
                state=request.query_params.get("state"),
                cursor=request.query_params.get("cursor"),
            )
        )


class CandidateApproveView(APIView):
    """POST /alumni/candidates/{id}/approve."""

    @extend_schema(
        operation_id="approve_alumni_candidate",
        request=ApproveCandidateRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, candidate_id: UUID) -> Response:
        """Include as AlumniProfile or exclude candidate."""
        body = validated(ApproveCandidateRequest, request.data)
        contact_policy = body.get("contact_policy")
        if contact_policy is not None:
            contact_policy = {
                "fields": contact_policy.get("fields"),
                "preferences": contact_policy.get("preferences"),
            }
        return Response(
            deps.candidate_service().approve(
                request.school_context,
                candidate_id,
                include=body["include"],
                reason=body["reason"],
                contact_policy=contact_policy,
            )
        )


class AlumniCollectionView(APIView):
    """GET /alumni."""

    @extend_schema(
        operation_id="list_alumni",
        parameters=[
            OpenApiParameter("year", int, required=False),
            OpenApiParameter("outcome", str, required=False),
            OpenApiParameter("cursor", str, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Scoped paginated alumni directory."""
        year_raw = request.query_params.get("year")
        year = int(year_raw) if year_raw not in (None, "") else None
        return Response(
            deps.profile_service().list_alumni(
                request.school_context,
                year=year,
                outcome=request.query_params.get("outcome"),
                cursor=request.query_params.get("cursor"),
            )
        )


class AlumniContactView(APIView):
    """PATCH /alumni/{id}/contact."""

    @extend_schema(
        operation_id="patch_alumni_contact",
        request=PatchContactRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def patch(self, request: Request, profile_id: UUID) -> Response:
        """Update contact fields and preferences."""
        body = validated(PatchContactRequest, request.data)
        return Response(
            deps.profile_service().patch_contact(
                request.school_context,
                profile_id,
                expected_version=body["expected_version"],
                reason=body["reason"],
                fields=body.get("fields"),
                preferences=body.get("preferences"),
            )
        )


class AlumniExportView(APIView):
    """POST /alumni/exports."""

    @extend_schema(
        operation_id="create_alumni_export",
        request=CreateExportRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Accept an export job for granted fields only."""
        body = validated(CreateExportRequest, request.data)
        result = deps.export_service().create_export(
            request.school_context,
            filters=dict(body.get("filters") or {}),
            fields=list(body["fields"]),
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)
