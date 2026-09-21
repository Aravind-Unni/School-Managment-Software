"""M14 REST endpoints for health, jobs, audit and restore rehearsals."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed

from . import deps
from .serializers import CreateRestoreRehearsalRequest, ErrorEnvelopeResponse, RetryJobRequest

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


class HealthLiveView(APIView):
    """GET /health/live — public."""

    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    @extend_schema(operation_id="health_live", responses={200: dict})
    def get(self, request: Request) -> Response:
        """Minimal public liveness."""
        return Response(deps.health_service().live())


class HealthReadyView(APIView):
    """GET /health/ready — authenticated detailed readiness."""

    @extend_schema(
        operation_id="health_ready",
        responses={200: dict, 503: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Database, queue and file-processor readiness."""
        body, code = deps.health_service().ready(request.school_context)
        return Response(body, status=code)


class JobDetailView(APIView):
    """GET /jobs/{id}."""

    @extend_schema(operation_id="get_job", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request, job_id: UUID) -> Response:
        """Scoped job progress and sanitized error."""
        return Response(deps.job_service().get(request.school_context, job_id))


class JobRetryView(APIView):
    """POST /jobs/{id}/retry."""

    @extend_schema(
        operation_id="retry_job",
        request=RetryJobRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, job_id: UUID) -> Response:
        """Replay a failed job while preserving business idempotency."""
        body = validated(RetryJobRequest, request.data)
        result = deps.job_service().retry(request.school_context, job_id, reason=body["reason"])
        return Response(result, status=status.HTTP_202_ACCEPTED)


class AuditCollectionView(APIView):
    """GET /audit."""

    @extend_schema(operation_id="list_audit", responses={200: dict, **COMMON_ERRORS})
    def get(self, request: Request) -> Response:
        """Read-only scoped audit records."""
        params = request.query_params
        actor_id = params.get("actor_id")
        aggregate_id = params.get("aggregate_id")
        occurred_from = params.get("occurred_from")
        occurred_to = params.get("occurred_to")
        try:
            result = deps.audit_service().list(
                request.school_context,
                action=params.get("action") or None,
                actor_id=UUID(actor_id) if actor_id else None,
                aggregate_id=UUID(aggregate_id) if aggregate_id else None,
                occurred_from=datetime.fromisoformat(occurred_from) if occurred_from else None,
                occurred_to=datetime.fromisoformat(occurred_to) if occurred_to else None,
                cursor=params.get("cursor") or None,
            )
        except ValueError as exc:
            raise ValidationFailed("error.validation_failed") from exc
        return Response(result)


class RestoreRehearsalCollectionView(APIView):
    """POST /operations/restore-rehearsals."""

    @extend_schema(
        operation_id="create_restore_rehearsal",
        request=CreateRestoreRehearsalRequest,
        responses={202: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Operator-only isolated restore rehearsal."""
        body = validated(CreateRestoreRehearsalRequest, request.data)
        result = deps.backup_service().create_restore_rehearsal(
            request.school_context,
            backup_manifest_id=body["backup_manifest_id"],
            isolated_target_label=body["isolated_target_label"],
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)
