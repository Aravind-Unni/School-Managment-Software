"""M13 REST endpoints for imports, exports, report cards and report snapshots.

Views parse, delegate and serialise. Every authorisation decision is made in
the services, so the port surface and the HTTP surface cannot disagree.
"""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed

from . import deps
from .serializers import (
    CommitImportRequest,
    CreateExportRequest,
    CreateImportRequest,
    CreateReportCardsRequest,
    ErrorEnvelopeResponse,
)

COMMON_ERRORS = {
    401: OpenApiResponse(ErrorEnvelopeResponse, "Unauthenticated."),
    403: OpenApiResponse(ErrorEnvelopeResponse, "Action denied."),
    404: OpenApiResponse(ErrorEnvelopeResponse, "Absent, or not visible."),
    409: OpenApiResponse(ErrorEnvelopeResponse, "Version or state conflict."),
    422: OpenApiResponse(ErrorEnvelopeResponse, "Business validation failed."),
}

#: Header that makes a commit replayable. Required by review-decisions item 13.
IDEMPOTENCY_HEADER = "HTTP_IDEMPOTENCY_KEY"


def validated(serializer_class, data) -> dict:
    """Parse a closed request body, raising 422 on anything unexpected."""
    payload = serializer_class(data=data)
    payload.is_valid(raise_exception=True)
    return payload.validated_data


def idempotency_key(request: Request) -> str:
    """Return the Idempotency-Key header, or raise 422 when it is absent.

    Required rather than generated: a key the server invented would be new on
    every retry, which is the opposite of what the header is for.
    """
    key = request.META.get(IDEMPOTENCY_HEADER, "").strip()
    if not key or len(key) > 128:
        raise ValidationFailed("error.validation_failed")
    return key


class ImportCollectionView(APIView):
    """POST /imports."""

    @extend_schema(
        operation_id="create_import",
        request=CreateImportRequest,
        responses={201: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Start a validate-only import job for an uploaded file."""
        body = validated(CreateImportRequest, request.data)
        result = deps.import_service().create(
            request.school_context,
            dataset=body["dataset"],
            file_ref=body["file_ref"],
            mode=body["mode"],
        )
        return Response(result, status=status.HTTP_201_CREATED)


class ImportDetailView(APIView):
    """GET /imports/{id}."""

    @extend_schema(operation_id="get_import", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, job_id: UUID) -> Response:
        """Import job status and counts."""
        return Response(deps.import_service().get(request.school_context, job_id))


class ImportCommitView(APIView):
    """POST /imports/{id}/commit."""

    @extend_schema(
        operation_id="commit_import",
        request=CommitImportRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, job_id: UUID) -> Response:
        """Apply validated rows after the digest and version checks pass."""
        key = idempotency_key(request)
        body = validated(CommitImportRequest, request.data)
        result = deps.import_service().commit(
            request.school_context,
            job_id,
            validation_version=body["validation_version"],
            source_digest=body["source_digest"],
            idempotency_key=key,
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)


class ImportErrorsView(APIView):
    """GET /imports/{id}/errors."""

    @extend_schema(operation_id="list_import_errors", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, job_id: UUID) -> Response:
        """Paginated row validation errors."""
        cursor = request.GET.get("cursor") or None
        return Response(
            deps.import_service().list_errors(request.school_context, job_id, cursor)
        )


class ImportTemplateView(APIView):
    """GET /import-templates/{dataset}."""

    @extend_schema(operation_id="get_import_template", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, dataset: str) -> Response:
        """Column schema for one import dataset."""
        return Response(deps.import_service().template(request.school_context, dataset))


class ExportCollectionView(APIView):
    """POST /exports."""

    @extend_schema(
        operation_id="create_export",
        request=CreateExportRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Enqueue an export job."""
        body = validated(CreateExportRequest, request.data)
        result = deps.export_service().create(
            request.school_context,
            dataset=body["dataset"],
            filters=dict(body["filters"]),
            fields=list(body["fields"]),
            export_format=body["format"],
            locale=body["locale"],
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)


class ExportDetailView(APIView):
    """GET /exports/{id}."""

    @extend_schema(operation_id="get_export", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, job_id: UUID) -> Response:
        """Export job status."""
        return Response(deps.export_service().get(request.school_context, job_id))


class ExportDownloadView(APIView):
    """GET /exports/{id}/download."""

    @extend_schema(operation_id="download_export", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, job_id: UUID) -> Response:
        """Short-lived authorised read URL for the export artifact."""
        access = deps.export_service().download(request.school_context, job_id)
        return Response(access.to_wire())


class ReportCardCollectionView(APIView):
    """POST /reportcards."""

    @extend_schema(
        operation_id="create_report_cards",
        request=CreateReportCardsRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Enqueue report card generation for one or more students."""
        body = validated(CreateReportCardsRequest, request.data)
        result = deps.report_card_service().create(
            request.school_context,
            publication_id=body["publication_id"],
            student_ids=list(body["student_ids"]),
            locale=body["locale"],
            template_version=body["template_version"],
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)


class ReportCardDetailView(APIView):
    """GET /reportcards/{id}."""

    @extend_schema(operation_id="get_report_card_job", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, job_id: UUID) -> Response:
        """Report card job status."""
        return Response(deps.report_card_service().get_job(request.school_context, job_id))


class ReportDetailView(APIView):
    """GET /reports/{id}."""

    @extend_schema(operation_id="get_report_snapshot", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, report_id: UUID) -> Response:
        """Immutable report snapshot metadata."""
        return Response(
            deps.report_card_service().get_snapshot(request.school_context, report_id)
        )


class ReportDownloadView(APIView):
    """GET /reports/{id}/download."""

    @extend_schema(operation_id="download_report", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, report_id: UUID) -> Response:
        """Short-lived authorised read URL for the report artifact."""
        access = deps.report_card_service().download(request.school_context, report_id)
        return Response(access.to_wire())
