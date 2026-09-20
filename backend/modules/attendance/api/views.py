"""M04 REST endpoints for attendance."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.errors import ValidationFailed

from . import deps
from .serializers import (
    CorrectionRequest,
    CreateSessionRequest,
    ErrorEnvelopeResponse,
    SaveSessionRequest,
    SubmitSessionRequest,
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


class PeriodListView(APIView):
    """GET /attendance/periods?date=."""

    @extend_schema(
        operation_id="list_authorized_periods",
        parameters=[OpenApiParameter("date", str, OpenApiParameter.QUERY, required=True)],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return the actor's authorised dated periods."""
        raw = request.query_params.get("date")
        if not raw:
            raise ValidationFailed("error.validation_failed")
        on = date.fromisoformat(raw)
        return Response(deps.draft_service().list_periods(request.school_context, on))


class SessionCollectionView(APIView):
    """POST /attendance/sessions."""

    @extend_schema(
        operation_id="create_or_get_session",
        request=CreateSessionRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request) -> Response:
        """Create a draft session or return the existing one."""
        body = validated(CreateSessionRequest, request.data)
        return Response(
            deps.draft_service().create_or_get(
                request.school_context,
                timetable_session_id=body["timetable_session_id"],
            )
        )


class SessionDetailView(APIView):
    """PUT /attendance/sessions/{id}."""

    @extend_schema(
        operation_id="save_session_entries",
        request=SaveSessionRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def put(self, request: Request, session_id: UUID) -> Response:
        """Save draft entries."""
        body = validated(SaveSessionRequest, request.data)
        return Response(
            deps.draft_service().save_entries(
                request.school_context,
                session_id=session_id,
                expected_version=body["expected_version"],
                entries=body["entries"],
            )
        )


class SessionSubmitView(APIView):
    """POST /attendance/sessions/{id}/submit."""

    @extend_schema(
        operation_id="submit_session",
        request=SubmitSessionRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, session_id: UUID) -> Response:
        """Submit a draft session. Requires Idempotency-Key."""
        body = validated(SubmitSessionRequest, request.data)
        key = request.headers.get("Idempotency-Key") or request.META.get(
            "HTTP_IDEMPOTENCY_KEY", ""
        )
        return Response(
            deps.submit_service().submit(
                request.school_context,
                session_id=session_id,
                expected_version=body["expected_version"],
                idempotency_key=key,
            )
        )


class EntryCorrectionView(APIView):
    """POST /attendance/entries/{id}/corrections."""

    @extend_schema(
        operation_id="correct_entry",
        request=CorrectionRequest,
        responses={200: dict, **COMMON_ERRORS},
    )
    def post(self, request: Request, entry_id: UUID) -> Response:
        """Apply an audited correction."""
        body = validated(CorrectionRequest, request.data)
        return Response(
            deps.correction_service().correct(
                request.school_context,
                entry_id=entry_id,
                status=body["status"],
                reason=body["reason"],
                expected_version=body["expected_version"],
            )
        )


class SummaryView(APIView):
    """GET /attendance/summary."""

    @extend_schema(
        operation_id="get_attendance_summary",
        parameters=[
            OpenApiParameter("student_id", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("from", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("to", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("subject_id", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: dict, **COMMON_ERRORS},
    )
    def get(self, request: Request) -> Response:
        """Return period-based counts for a student."""
        student_raw = request.query_params.get("student_id")
        from_raw = request.query_params.get("from")
        to_raw = request.query_params.get("to")
        if not student_raw or not from_raw or not to_raw:
            raise ValidationFailed("error.validation_failed")
        subject_raw = request.query_params.get("subject_id")
        summary = deps.summary_service().get_summary(
            request.school_context,
            UUID(student_raw),
            date.fromisoformat(from_raw),
            date.fromisoformat(to_raw),
            subject_id=UUID(subject_raw) if subject_raw else None,
        )
        return Response(
            {
                "unit": summary.unit,
                "student_id": str(summary.student_id),
                "from_date": summary.from_date.isoformat(),
                "to_date": summary.to_date.isoformat(),
                "subject_id": str(summary.subject_id) if summary.subject_id else None,
                "eligible": summary.eligible,
                "marked": summary.marked,
                "present": summary.present,
                "absent": summary.absent,
                "late": summary.late,
                "excused": summary.excused,
                "unmarked": summary.unmarked,
                "percentage": summary.percentage,
                "policy_version": summary.policy_version,
                "updated_at": summary.updated_at.isoformat(),
            }
        )
