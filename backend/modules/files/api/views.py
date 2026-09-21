"""M12 REST endpoints for uploads, status, quality, reprocess and retention."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.wire import file_to_wire
from . import deps
from .serializers import (
    BeginUploadRequest,
    CompleteUploadRequest,
    ErrorEnvelopeResponse,
    QualityConfirmationRequest,
    ReprocessRequest,
    RetentionHoldRequest,
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


class UploadCollectionView(APIView):
    """POST /uploads."""

    @extend_schema(
        operation_id="begin_upload",
        request=BeginUploadRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Open a scoped upload session."""
        body = validated(BeginUploadRequest, request.data)
        session = deps.lifecycle_service().begin_upload(
            request.school_context,
            purpose=body["purpose"],
            client_name=body["client_name"],
            declared_bytes=body["declared_bytes"],
            mime=body["mime"],
        )
        return Response(
            {
                "id": str(session.id),
                "upload_url": session.upload_url,
                "expires_at": session.expires_at.isoformat().replace("+00:00", "Z"),
                "max_bytes": session.max_bytes,
            },
            status=status.HTTP_201_CREATED,
        )


class UploadCompleteView(APIView):
    """POST /uploads/{id}/complete."""

    @extend_schema(
        operation_id="complete_upload",
        request=CompleteUploadRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, upload_id: UUID) -> Response:
        """Verify quarantine bytes and enqueue processing."""
        body = validated(CompleteUploadRequest, request.data)
        result = deps.lifecycle_service().complete_upload(
            request.school_context, upload_id, body["source_sha256"]
        )
        return Response(result, status=status.HTTP_201_CREATED)


class UploadBytesView(APIView):
    """PUT /uploads/{id}/bytes — quarantine put for memory-store profiles."""

    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    @extend_schema(operation_id="put_upload_bytes", responses={204: None, **COMMON_ERRORS})
    def put(self, request: Request, upload_id: UUID) -> Response:
        """Accept raw body into quarantine using the session put token."""
        token = request.GET.get("token", "")
        deps.lifecycle_service().put_quarantine_bytes(upload_id, token, request.body)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FileStatusView(APIView):
    """GET /files/{id}/status."""

    @extend_schema(operation_id="get_file_status", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, file_id: UUID) -> Response:
        """File state and candidate metadata."""
        dto = deps.files_port().get_status(request.school_context, file_id)
        from ..models import File

        row = File.objects.get(id=dto.id)
        return Response(file_to_wire(row))


class QualityConfirmationView(APIView):
    """POST /files/{id}/quality-confirmation."""

    @extend_schema(
        operation_id="confirm_file_quality",
        request=QualityConfirmationRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, file_id: UUID) -> Response:
        """Teacher confirms candidate readability."""
        body = validated(QualityConfirmationRequest, request.data)
        return Response(
            deps.lifecycle_service().confirm_quality(
                request.school_context, file_id, body["candidate_version"]
            )
        )


class ReprocessView(APIView):
    """POST /files/{id}/reprocess."""

    @extend_schema(
        operation_id="reprocess_file",
        request=ReprocessRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, file_id: UUID) -> Response:
        """Enqueue higher-fidelity candidate."""
        body = validated(ReprocessRequest, request.data)
        result = deps.lifecycle_service().reprocess(
            request.school_context, file_id, reason=body["reason"]
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)


class RetentionHoldView(APIView):
    """POST /files/{id}/retention-hold."""

    @extend_schema(
        operation_id="set_retention_hold",
        request=RetentionHoldRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, file_id: UUID) -> Response:
        """Set or clear legal hold (recent 2FA)."""
        body = validated(RetentionHoldRequest, request.data)
        return Response(
            deps.retention_service().set_retention_hold(
                request.school_context,
                file_id,
                legal_hold=body["legal_hold"],
                expected_version=body["expected_version"],
                reason=body.get("reason"),
            )
        )


class FileBytesView(APIView):
    """GET /file-bytes/{id}?token=... -- serve one file version for a signed link.

    No session is needed: the token IS the authorisation, minted by
    FilesPort.issue_read after the Access check, bound to this file and
    version, and valid for the policy's signed-read lifetime only.
    """

    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    @extend_schema(operation_id="get_file_bytes", responses={200: bytes, **COMMON_ERRORS})
    def get(self, request: Request, file_id: UUID) -> Response:
        """Serve canonical bytes when the token verifies; 404 otherwise."""
        from ..models import Derivative, File, FilesPolicy
        from ..services import read_tokens
        from ..services.storage import object_store

        row = File.objects.filter(id=file_id).first()
        if row is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        policy = FilesPolicy.objects.filter(school_id=row.school_id).first()
        lifetime = policy.signed_read_seconds if policy else 60
        version = read_tokens.verify(
            request.GET.get("token", ""), file_id=file_id, max_age_seconds=lifetime
        )
        if version is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        derivative = Derivative.objects.filter(
            file_id=file_id, kind="canonical", version=version
        ).first()
        if derivative is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        body = object_store().get(derivative.storage_key)
        response = HttpResponse(body, content_type=derivative.mime)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
